from unittest.mock import MagicMock, patch
from backend.agents.snowflake_context import find_recent_query_run, fetch_query_kpis
from backend.models.kpi_models import QueryKPIs


def _make_cursor(fetchone_return=None):
    cur = MagicMock()
    cur.fetchone.return_value = fetchone_return
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


def test_find_recent_query_run_returns_id_when_found():
    conn, cur = _make_cursor({"QUERY_ID": "abc-123"})
    result = find_recent_query_run(conn, "SELECT * FROM orders")
    assert result == "abc-123"
    cur.execute.assert_called_once()


def test_find_recent_query_run_returns_none_when_not_found():
    conn, cur = _make_cursor(None)
    result = find_recent_query_run(conn, "SELECT id FROM orders")
    assert result is None


def test_fetch_query_kpis_populates_fields():
    row = {
        "QUERY_ID": "qid-1",
        "TOTAL_ELAPSED_TIME": 2000,
        "BYTES_SCANNED": 1_000_000,
        "BYTES_SPILLED_TO_LOCAL_STORAGE": 0,
        "BYTES_SPILLED_TO_REMOTE_STORAGE": 0,
        "PARTITIONS_SCANNED": 5,
        "PARTITIONS_TOTAL": 10,
        "ROWS_PRODUCED": 100,
        "CREDITS_USED_CLOUD_SERVICES": 0.001,
    }
    conn, _ = _make_cursor(row)
    result = fetch_query_kpis(conn, "qid-1", source="history")
    assert isinstance(result, QueryKPIs)
    assert result.query_id == "qid-1"
    assert result.elapsed_ms == 2000
    assert result.bytes_scanned == 1_000_000
    assert result.partitions_scanned == 5
    assert result.credits == 0.001
    assert result.source == "history"
    assert result.error is None


def test_fetch_query_kpis_returns_error_when_not_found():
    conn, _ = _make_cursor(None)
    result = fetch_query_kpis(conn, "missing-id", source="live")
    assert result.error is not None
    assert "missing-id" in result.error
    assert result.elapsed_ms is None
