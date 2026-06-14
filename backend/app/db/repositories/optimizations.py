from __future__ import annotations
import json
from typing import Any
from app.db.connection import get_pool


async def insert_optimization(
    query_id: str,
    diagnosis: dict[str, Any],
    variants: list[dict[str, Any]],
    cost_predictions: dict[str, Any],
    validation_results: dict[str, Any],
    recommended_variant: str | None,
) -> str:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO optimizations
                (query_id, diagnosis, variants, cost_predictions, validation_results, recommended_variant, status)
            VALUES ($1::uuid, $2::jsonb, $3::jsonb, $4::jsonb, $5::jsonb, $6, 'pending_review')
            RETURNING optimization_id::text
            """,
            query_id,
            json.dumps(diagnosis),
            json.dumps(variants),
            json.dumps(cost_predictions),
            json.dumps(validation_results),
            recommended_variant,
        )
    return row["optimization_id"]


async def get_optimization_by_id(optimization_id: str) -> dict[str, Any] | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT optimization_id::text, query_id::text, diagnosis, variants,
                   cost_predictions, validation_results, recommended_variant,
                   user_selected_variant, status, created_at, updated_at
            FROM optimizations WHERE optimization_id = $1::uuid
            """,
            optimization_id,
        )
    if not row:
        return None
    d = dict(row)
    for field in ("diagnosis", "variants", "cost_predictions", "validation_results"):
        v = d[field]
        if isinstance(v, str):
            d[field] = json.loads(v)
        elif v is None:
            d[field] = {} if field != "variants" else []
    return d


async def list_optimizations(
    status: str | None = None,
    query_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    pool = get_pool()
    conditions = []
    params: list[Any] = []
    if status:
        params.append(status)
        conditions.append(f"status = ${len(params)}")
    if query_id:
        params.append(query_id)
        conditions.append(f"query_id = ${len(params)}::uuid")
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT optimization_id::text, query_id::text, diagnosis, variants,
                   cost_predictions, validation_results, recommended_variant,
                   user_selected_variant, status, created_at, updated_at
            FROM optimizations {where}
            ORDER BY created_at DESC LIMIT {limit}
            """,
            *params,
        )
    result = []
    for row in rows:
        d = dict(row)
        for field in ("diagnosis", "variants", "cost_predictions", "validation_results"):
            v = d[field]
            if isinstance(v, str):
                d[field] = json.loads(v)
            elif v is None:
                d[field] = {} if field != "variants" else []
        result.append(d)
    return result


async def update_optimization_status(
    optimization_id: str,
    status: str,
    user_selected_variant: str | None = None,
) -> None:
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE optimizations
            SET status = $1, user_selected_variant = COALESCE($2, user_selected_variant),
                updated_at = NOW()
            WHERE optimization_id = $3::uuid
            """,
            status, user_selected_variant, optimization_id,
        )


async def update_variant_sql(optimization_id: str, variant_id: str, new_sql: str) -> None:
    """Replace variant SQL and clear requires_human_edit flag in the JSONB array."""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE optimizations
            SET variants = (
                SELECT jsonb_agg(
                    CASE WHEN v->>'id' = $2
                    THEN v || jsonb_build_object('sql', $3, 'requires_human_edit', false, 'human_edited', true)
                    ELSE v
                    END
                )
                FROM jsonb_array_elements(variants) AS v
            ),
            updated_at = NOW()
            WHERE optimization_id = $1::uuid
            """,
            optimization_id, variant_id, new_sql,
        )


async def update_query_status(query_id: str, status: str) -> None:
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE queries SET status = $1 WHERE query_id = $2::uuid",
            status, query_id,
        )
