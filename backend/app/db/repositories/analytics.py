from __future__ import annotations
from typing import Any
from app.db.connection import get_pool


async def savings_summary() -> dict[str, Any]:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                COUNT(*) FILTER (WHERE o.status = 'approved') AS total_optimizations,
                COUNT(DISTINCT q.query_id)                     AS total_queries,
                COALESCE(SUM(
                    ((o.cost_predictions->'variants'->0->>'savings_credits')::float)
                ) FILTER (WHERE o.status = 'approved'), 0)    AS total_credits_saved,
                COALESCE(AVG(
                    ((o.cost_predictions->'variants'->0->>'savings_pct')::float)
                ) FILTER (WHERE o.status = 'approved'), 0)    AS avg_savings_pct
            FROM optimizations o
            JOIN queries q ON q.query_id = o.query_id
        """)
    return {
        "total_optimizations": int(row["total_optimizations"] or 0),
        "total_queries": int(row["total_queries"] or 0),
        "total_credits_saved": round(float(row["total_credits_saved"] or 0), 2),
        "avg_savings_pct": round(float(row["avg_savings_pct"] or 0), 1),
    }


async def savings_by_month() -> list[dict[str, Any]]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                TO_CHAR(o.created_at, 'YYYY-MM') AS month,
                COUNT(*)                           AS optimization_count,
                COALESCE(SUM(
                    (o.cost_predictions->'variants'->0->>'savings_credits')::float
                ), 0)                              AS credits_saved
            FROM optimizations o
            WHERE o.status = 'approved'
            GROUP BY TO_CHAR(o.created_at, 'YYYY-MM')
            ORDER BY month
            LIMIT 12
        """)
    return [
        {
            "month": r["month"],
            "optimization_count": int(r["optimization_count"]),
            "credits_saved": round(float(r["credits_saved"]), 2),
        }
        for r in rows
    ]


async def savings_by_team() -> list[dict[str, Any]]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                COALESCE(t.name, 'Unassigned') AS team_name,
                COALESCE(SUM(
                    (o.cost_predictions->'variants'->0->>'savings_credits')::float
                ), 0)                           AS credits_saved,
                COUNT(*)                        AS optimization_count
            FROM optimizations o
            JOIN queries q ON q.query_id = o.query_id
            LEFT JOIN teams t ON t.team_id = q.team_id
            WHERE o.status = 'approved'
            GROUP BY COALESCE(t.name, 'Unassigned')
            ORDER BY credits_saved DESC
            LIMIT 10
        """)
    return [
        {
            "team_name": r["team_name"],
            "credits_saved": round(float(r["credits_saved"]), 2),
            "optimization_count": int(r["optimization_count"]),
        }
        for r in rows
    ]


async def technique_effectiveness() -> list[dict[str, Any]]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT name, category, success_rate, failure_rate, application_count
            FROM techniques
            ORDER BY success_rate DESC, application_count DESC
        """)
    return [
        {
            "name": r["name"],
            "category": r["category"],
            "success_rate": round(float(r["success_rate"] or 0), 3),
            "failure_rate": round(float(r["failure_rate"] or 0), 3),
            "application_count": int(r["application_count"] or 0),
        }
        for r in rows
    ]
