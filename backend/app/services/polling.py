from __future__ import annotations
import asyncio
import logging

from app.services.snowflake import fetch_recent_queries
from app.services.classifier import classify
from app.db.repositories.queries import insert_query, query_exists

logger = logging.getLogger(__name__)
_POLL_INTERVAL_SECONDS = 300


async def _run_once() -> int:
    rows = await fetch_recent_queries()
    ingested = 0
    for row in rows:
        if await query_exists(row["query_hash"]):
            continue
        cl, sev, issue = classify(row["query_text"], row["execution_metrics"])
        await insert_query(
            query_text=row["query_text"],
            query_hash=row["query_hash"],
            query_preview=row["query_preview"],
            warehouse=row.get("warehouse"),
            warehouse_size=row.get("warehouse_size"),
            execution_metrics=row["execution_metrics"],
            severity=sev,
            issue_type=issue,
            classification=cl,
            source=row.get("source", "snowflake"),
        )
        ingested += 1
    logger.info("Polling cycle complete", extra={"ingested": ingested, "total": len(rows)})
    return ingested


async def start_polling() -> None:
    while True:
        try:
            await _run_once()
        except Exception:
            logger.error("Polling error", exc_info=True)
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
