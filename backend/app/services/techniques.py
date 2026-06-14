from __future__ import annotations
import logging
from app.db.connection import get_pool

logger = logging.getLogger(__name__)

_TECHNIQUES = [
    ("Partition Filter Push-Down", "scan_reduction",  0.82, 0.05, 0),
    ("Column Projection",          "scan_reduction",  0.75, 0.08, 0),
    ("CTE Refactor",               "readability",     0.68, 0.12, 0),
    ("Join Order Optimization",    "join_efficiency", 0.71, 0.10, 0),
    ("QUALIFY Deduplication",      "deduplication",   0.79, 0.07, 0),
    ("Warehouse Right-Sizing",     "cost_reduction",  0.88, 0.04, 0),
]


async def seed_techniques() -> None:
    pool = get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchval("SELECT COUNT(*) FROM techniques")
        if existing > 0:
            return
        for name, category, success_rate, failure_rate, application_count in _TECHNIQUES:
            await conn.execute(
                """
                INSERT INTO techniques (name, category, success_rate, failure_rate, application_count)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (name) DO NOTHING
                """,
                name, category, success_rate, failure_rate, application_count,
            )
    logger.info("Seeded %d techniques", len(_TECHNIQUES))
