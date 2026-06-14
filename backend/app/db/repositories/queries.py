from __future__ import annotations
import json
from typing import Any
import asyncpg
from app.db.connection import get_pool


async def insert_query(
    query_text: str,
    query_hash: str,
    query_preview: str | None,
    warehouse: str | None,
    warehouse_size: str | None,
    execution_metrics: dict[str, Any],
    severity: str | None,
    issue_type: str | None,
    classification: str | None,
    source: str = "snowflake",
) -> str:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO queries
                (query_text, query_hash, query_preview, warehouse, warehouse_size,
                 execution_metrics, severity, issue_type, classification, source)
            VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9,$10)
            ON CONFLICT DO NOTHING
            RETURNING query_id::text
            """,
            query_text, query_hash, query_preview, warehouse, warehouse_size,
            json.dumps(execution_metrics), severity, issue_type, classification, source,
        )
    return row["query_id"] if row else ""


async def query_exists(query_hash: str) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM queries WHERE query_hash = $1 LIMIT 1", query_hash
        )
    return row is not None


async def list_queries(
    limit: int = 50,
    offset: int = 0,
    severity: str | None = None,
    team_id: str | None = None,
    status: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    pool = get_pool()
    filters: list[str] = []
    params: list[Any] = []
    idx = 1

    if severity:
        filters.append(f"severity = ${idx}")
        params.append(severity)
        idx += 1
    if team_id:
        filters.append(f"team_id = ${idx}::uuid")
        params.append(team_id)
        idx += 1
    if status:
        filters.append(f"status = ${idx}")
        params.append(status)
        idx += 1

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    async with pool.acquire() as conn:
        count_row = await conn.fetchrow(f"SELECT COUNT(*) FROM queries {where}", *params)
        total = count_row["count"]

        rows = await conn.fetch(
            f"""
            SELECT query_id::text, query_preview, team_id::text, warehouse,
                   warehouse_size, severity, issue_type, status,
                   ingestion_timestamp, execution_metrics
            FROM queries {where}
            ORDER BY ingestion_timestamp DESC
            LIMIT ${idx} OFFSET ${idx+1}
            """,
            *params, limit, offset,
        )

    items = []
    for r in rows:
        d = dict(r)
        raw_metrics = d["execution_metrics"]
        if isinstance(raw_metrics, str):
            d["execution_metrics"] = json.loads(raw_metrics)
        elif raw_metrics is None:
            d["execution_metrics"] = {}
        items.append(d)

    return items, total


async def get_query_by_id(query_id: str) -> dict[str, Any] | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT query_id::text, query_text, query_hash, query_preview,
                   team_id::text, warehouse, warehouse_size, classification,
                   severity, issue_type, execution_metrics,
                   ingestion_timestamp, source, status
            FROM queries WHERE query_id = $1::uuid
            """,
            query_id,
        )
    if not row:
        return None
    d = dict(row)
    raw_metrics = d["execution_metrics"]
    if isinstance(raw_metrics, str):
        d["execution_metrics"] = json.loads(raw_metrics)
    elif raw_metrics is None:
        d["execution_metrics"] = {}
    return d
