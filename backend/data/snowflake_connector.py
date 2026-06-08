import threading
from typing import Optional, Dict, Any, List

_lock = threading.Lock()
_conn = None
_creds: Optional[Dict[str, str]] = None

_SQL: Dict[str, str] = {
    "credits": """
        SELECT
            QUERY_PARAMETERIZED_HASH         AS query_id,
            ANY_VALUE(QUERY_TEXT)            AS query_text,
            SUM(CREDITS_USED_CLOUD_SERVICES) AS credits,
            COUNT(*)                         AS frequency,
            NULL                             AS score
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD('days', -30, CURRENT_TIMESTAMP())
          AND EXECUTION_STATUS = 'SUCCESS'
          AND QUERY_TEXT IS NOT NULL
        GROUP BY QUERY_PARAMETERIZED_HASH
        ORDER BY credits DESC NULLS LAST
        LIMIT 100
    """,
    "frequency": """
        SELECT
            QUERY_PARAMETERIZED_HASH         AS query_id,
            ANY_VALUE(QUERY_TEXT)            AS query_text,
            SUM(CREDITS_USED_CLOUD_SERVICES) AS credits,
            COUNT(*)                         AS frequency,
            NULL                             AS score
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD('days', -30, CURRENT_TIMESTAMP())
          AND EXECUTION_STATUS = 'SUCCESS'
          AND QUERY_TEXT IS NOT NULL
        GROUP BY QUERY_PARAMETERIZED_HASH
        ORDER BY frequency DESC NULLS LAST
        LIMIT 100
    """,
    "killer": """
        SELECT
            QUERY_PARAMETERIZED_HASH                          AS query_id,
            ANY_VALUE(QUERY_TEXT)                             AS query_text,
            SUM(CREDITS_USED_CLOUD_SERVICES)                  AS credits,
            COUNT(*)                                          AS frequency,
            (SUM(CREDITS_USED_CLOUD_SERVICES) * COUNT(*))     AS score
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD('days', -30, CURRENT_TIMESTAMP())
          AND EXECUTION_STATUS = 'SUCCESS'
          AND QUERY_TEXT IS NOT NULL
        GROUP BY QUERY_PARAMETERIZED_HASH
        ORDER BY score DESC NULLS LAST
        LIMIT 100
    """,
    "all": """
        SELECT
            QUERY_ID                    AS query_id,
            QUERY_TEXT                  AS query_text,
            CREDITS_USED_CLOUD_SERVICES AS credits,
            NULL                        AS frequency,
            NULL                        AS score
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE START_TIME >= DATEADD('days', -30, CURRENT_TIMESTAMP())
          AND QUERY_TEXT IS NOT NULL
        ORDER BY START_TIME DESC
        LIMIT 500
    """,
}


def connect(credentials: Dict[str, str]) -> None:
    import snowflake.connector
    global _conn, _creds
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
        conn = snowflake.connector.connect(
            account=credentials["account"],
            user=credentials["user"],
            password=credentials["password"],
            role=credentials.get("role") or None,
            warehouse=credentials.get("warehouse") or None,
            database=credentials.get("database") or None,
            schema=credentials.get("schema_name") or None,
        )
        cur = conn.cursor()
        try:
            cur.execute("SELECT 1")
        finally:
            cur.close()
        _conn = conn
        _creds = credentials


def is_connected() -> bool:
    if _conn is None:
        return False
    try:
        cur = _conn.cursor()
        try:
            cur.execute("SELECT 1")
            return True
        finally:
            cur.close()
    except Exception:
        return False


def get_account() -> Optional[str]:
    return _creds.get("account") if _creds else None


def disconnect() -> None:
    global _conn, _creds
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
        _conn = None
        _creds = None


def fetch_queries(category: str) -> List[Dict[str, Any]]:
    import snowflake.connector
    if _conn is None:
        raise RuntimeError("Not connected to Snowflake")
    sql = _SQL.get(category)
    if sql is None:
        raise ValueError(f"Unknown category: {category!r}. Must be one of: {list(_SQL)}")
    cursor = _conn.cursor(snowflake.connector.DictCursor)
    cursor.execute(sql)
    rows = cursor.fetchall()
    result = []
    for row in rows:
        result.append({
            "query_id": str(row.get("QUERY_ID") or ""),
            "query_text": str(row.get("QUERY_TEXT") or ""),
            "credits": float(row.get("CREDITS") or 0),
            "frequency": int(row["FREQUENCY"]) if row.get("FREQUENCY") is not None else None,
            "score": float(row["SCORE"]) if row.get("SCORE") is not None else None,
        })
    return result
