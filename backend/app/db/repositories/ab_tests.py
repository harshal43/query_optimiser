from __future__ import annotations
import json
from typing import Any
from app.db.connection import get_pool


async def create_ab_test(query_id: str, optimization_id: str) -> str:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO ab_tests (query_id, optimization_id, traffic_split, status)
            VALUES ($1::uuid, $2::uuid, $3::jsonb, 'shadow')
            RETURNING test_id::text
            """,
            query_id, optimization_id,
            json.dumps({"control": 100, "optimized": 0}),
        )
    return row["test_id"]


async def get_ab_test(test_id: str) -> dict[str, Any] | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT test_id::text, query_id::text, optimization_id::text,
                   traffic_split, control_metrics, variant_metrics,
                   status, p_value, started_at, completed_at
            FROM ab_tests WHERE test_id = $1::uuid
            """, test_id,
        )
    if not row:
        return None
    d = dict(row)
    for f in ("traffic_split", "control_metrics", "variant_metrics"):
        v = d[f]
        d[f] = json.loads(v) if isinstance(v, str) else (v or {})
    return d


async def list_ab_tests(status: str | None = None) -> list[dict[str, Any]]:
    pool = get_pool()
    where = "WHERE status = $1" if status else ""
    params = [status] if status else []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT test_id::text, query_id::text, optimization_id::text,
                   traffic_split, control_metrics, variant_metrics,
                   status, p_value, started_at, completed_at
            FROM ab_tests {where} ORDER BY started_at DESC LIMIT 100
            """, *params,
        )
    result = []
    for row in rows:
        d = dict(row)
        for f in ("traffic_split", "control_metrics", "variant_metrics"):
            v = d[f]
            d[f] = json.loads(v) if isinstance(v, str) else (v or {})
        result.append(d)
    return result


async def update_ab_test(
    test_id: str,
    status: str | None = None,
    traffic_split: dict[str, Any] | None = None,
    p_value: float | None = None,
) -> None:
    pool = get_pool()
    sets = []
    params: list[Any] = []
    idx = 1
    if status:
        sets.append(f"status = ${idx}"); params.append(status); idx += 1
    if traffic_split:
        sets.append(f"traffic_split = ${idx}::jsonb"); params.append(json.dumps(traffic_split)); idx += 1
    if p_value is not None:
        sets.append(f"p_value = ${idx}"); params.append(p_value); idx += 1
    if not sets:
        return
    completed_clause = ", completed_at = NOW()" if status in ("completed", "rolled_back") else ""
    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE ab_tests SET {', '.join(sets)}{completed_clause} WHERE test_id = ${idx}::uuid",
            *params, test_id,
        )
