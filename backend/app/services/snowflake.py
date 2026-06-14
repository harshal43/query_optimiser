from __future__ import annotations
import asyncio
import hashlib
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_SEED_QUERIES: list[dict[str, Any]] = [
    {
        "query_text": "SELECT * FROM SALES.PUBLIC.ORDERS o JOIN SALES.PUBLIC.ORDER_ITEMS i ON o.order_id = i.order_id JOIN SALES.PUBLIC.PRODUCTS p ON p.product_id = i.product_id WHERE o.created_at >= DATEADD(day, -90, CURRENT_TIMESTAMP())",
        "warehouse": "COMPUTE_WH",
        "warehouse_size": "X-Small",
        "execution_metrics": {"execution_time_ms": 45200, "bytes_scanned": 4_200_000_000, "bytes_spilled_remote": 0, "credits_used": 12.4, "rows_produced": 2_800_000},
    },
    {
        "query_text": "SELECT user_id, COUNT(*) as event_count, SUM(revenue) as total_revenue FROM ANALYTICS.EVENTS GROUP BY user_id ORDER BY total_revenue DESC LIMIT 1000",
        "warehouse": "ANALYTICS_WH",
        "warehouse_size": "Small",
        "execution_metrics": {"execution_time_ms": 22400, "bytes_scanned": 890_000_000, "bytes_spilled_remote": 120_000_000, "credits_used": 3.2, "rows_produced": 1000},
    },
    {
        "query_text": "SELECT * FROM RAW.CLICKSTREAM.EVENTS WHERE session_id IN (SELECT session_id FROM RAW.CLICKSTREAM.SESSIONS WHERE user_id IN (SELECT user_id FROM CRM.USERS WHERE country = 'US'))",
        "warehouse": "COMPUTE_WH",
        "warehouse_size": "Medium",
        "execution_metrics": {"execution_time_ms": 78900, "bytes_scanned": 12_000_000_000, "bytes_spilled_remote": 0, "credits_used": 28.7, "rows_produced": 45_000},
    },
    {
        "query_text": "SELECT product_id, SUM(quantity) FROM ORDERS.LINE_ITEMS WHERE created_at BETWEEN '2024-01-01' AND '2024-12-31' GROUP BY product_id",
        "warehouse": "REPORTING_WH",
        "warehouse_size": "X-Small",
        "execution_metrics": {"execution_time_ms": 3200, "bytes_scanned": 240_000_000, "bytes_spilled_remote": 0, "credits_used": 0.8, "rows_produced": 12_400},
    },
    {
        "query_text": "SELECT id FROM users WHERE id = 42",
        "warehouse": "COMPUTE_WH",
        "warehouse_size": "X-Small",
        "execution_metrics": {"execution_time_ms": 120, "credits_used": 0.15, "bytes_scanned": 1_000, "rows_produced": 1},
    },
    {
        "query_text": "SELECT a.*, b.*, c.*, d.*, e.* FROM TABLE_A a JOIN TABLE_B b ON a.id = b.a_id JOIN TABLE_C c ON b.id = c.b_id JOIN TABLE_D d ON c.id = d.c_id JOIN TABLE_E e ON d.id = e.d_id JOIN TABLE_F f ON e.id = f.e_id WHERE a.status = 'active'",
        "warehouse": "COMPUTE_WH",
        "warehouse_size": "Large",
        "execution_metrics": {"execution_time_ms": 92000, "bytes_scanned": 8_000_000_000, "bytes_spilled_remote": 50_000_000, "credits_used": 45.2, "rows_produced": 890_000},
    },
]


def _make_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:32]


def _make_preview(text: str, max_len: int = 120) -> str:
    single = " ".join(text.split())
    return single[:max_len] + ("…" if len(single) > max_len else "")


async def fetch_recent_queries() -> list[dict[str, Any]]:
    """Return rows to ingest. Falls back to seed data if Snowflake not configured."""
    if not settings.snowflake_account:
        logger.info("Snowflake not configured — using seed data")
        return _build_seed_rows()
    return await _fetch_from_snowflake()


def _build_seed_rows() -> list[dict[str, Any]]:
    rows = []
    for q in _SEED_QUERIES:
        rows.append({
            "query_text": q["query_text"],
            "query_hash": _make_hash(q["query_text"]),
            "query_preview": _make_preview(q["query_text"]),
            "warehouse": q.get("warehouse"),
            "warehouse_size": q.get("warehouse_size"),
            "execution_metrics": q.get("execution_metrics", {}),
            "source": "seed",
        })
    return rows


async def _fetch_from_snowflake() -> list[dict[str, Any]]:
    return await asyncio.get_event_loop().run_in_executor(None, _sync_fetch)


def _sync_fetch() -> list[dict[str, Any]]:
    import snowflake.connector  # type: ignore

    connect_kwargs: dict[str, Any] = {
        "account": settings.snowflake_account,
        "user": settings.snowflake_user,
        "role": settings.snowflake_role,
        "warehouse": settings.snowflake_warehouse,
        "database": settings.snowflake_database,
        "schema": settings.snowflake_schema,
    }

    if settings.snowflake_private_key_path:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key  # type: ignore
        with open(settings.snowflake_private_key_path, "rb") as f:
            private_key = load_pem_private_key(f.read(), password=None)
        from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption  # type: ignore
        connect_kwargs["private_key"] = private_key.private_bytes(
            encoding=Encoding.DER,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        )
    else:
        raise RuntimeError("snowflake_private_key_path required for key-pair auth")

    conn = snowflake.connector.connect(**connect_kwargs)
    try:
        cursor = conn.cursor(snowflake.connector.DictCursor)
        cursor.execute("""
            SELECT
                QUERY_TEXT,
                WAREHOUSE_NAME,
                WAREHOUSE_SIZE,
                EXECUTION_TIME / 1000.0        AS execution_time_ms,
                BYTES_SCANNED,
                BYTES_SPILLED_TO_REMOTE_STORAGE AS bytes_spilled_remote,
                CREDITS_USED_CLOUD_SERVICES    AS credits_used,
                ROWS_PRODUCED
            FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
            WHERE START_TIME >= DATEADD(day, -30, CURRENT_TIMESTAMP())
              AND EXECUTION_STATUS = 'SUCCESS'
              AND QUERY_TYPE = 'SELECT'
              AND TOTAL_ELAPSED_TIME > 1000
            ORDER BY TOTAL_ELAPSED_TIME DESC
            LIMIT 500
        """)
        rows = []
        for r in cursor.fetchall():
            text = r.get("QUERY_TEXT") or ""
            rows.append({
                "query_text": text,
                "query_hash": _make_hash(text),
                "query_preview": _make_preview(text),
                "warehouse": r.get("WAREHOUSE_NAME"),
                "warehouse_size": r.get("WAREHOUSE_SIZE"),
                "execution_metrics": {
                    "execution_time_ms": float(r.get("EXECUTION_TIME_MS") or 0),
                    "bytes_scanned": int(r.get("BYTES_SCANNED") or 0),
                    "bytes_spilled_remote": int(r.get("BYTES_SPILLED_REMOTE") or 0),
                    "credits_used": float(r.get("CREDITS_USED") or 0),
                    "rows_produced": int(r.get("ROWS_PRODUCED") or 0),
                },
                "source": "snowflake",
            })
        return rows
    finally:
        conn.close()
