import threading
from typing import Optional, Dict, Any, List

_lock = threading.Lock()
_conn = None
_creds: Optional[Dict[str, str]] = None

_CREDITS_SQL = """
    SELECT
        QUERY_PARAMETERIZED_HASH         AS query_id,
        ANY_VALUE(QUERY_TEXT)            AS query_text,
        SUM(CREDITS_USED_CLOUD_SERVICES) AS credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD('days', -30, CURRENT_TIMESTAMP())
      AND EXECUTION_STATUS = 'SUCCESS'
      AND QUERY_TEXT IS NOT NULL
    GROUP BY QUERY_PARAMETERIZED_HASH
    ORDER BY credits DESC NULLS LAST
    LIMIT 100
"""


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


def fetch_queries(category: str = "credits") -> List[Dict[str, Any]]:
    import snowflake.connector
    if _conn is None:
        raise RuntimeError("Not connected to Snowflake")
    cursor = _conn.cursor(snowflake.connector.DictCursor)
    cursor.execute(_CREDITS_SQL)
    rows = cursor.fetchall()
    return [
        {
            "query_id":   str(row.get("QUERY_ID") or row.get("query_id") or ""),
            "query_text": str(row.get("QUERY_TEXT") or row.get("query_text") or ""),
            "credits":    float(row.get("CREDITS") or row.get("credits") or 0),
        }
        for row in rows
    ]
