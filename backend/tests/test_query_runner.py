import pytest
from unittest.mock import MagicMock, patch
from backend.agents.query_runner import (
    _add_limit,
    execute_and_capture,
    _compute_improvement,
    build_comparison,
)
from backend.models.kpi_models import QueryKPIs, ComparisonResult


# ── _add_limit ────────────────────────────────────────────────────────────────

def test_add_limit_appends_when_absent():
    result = _add_limit("SELECT * FROM orders", 100)
    assert "LIMIT 100" in result.upper()


def test_add_limit_preserves_existing_limit():
    result = _add_limit("SELECT * FROM orders LIMIT 5", 100)
    assert "LIMIT 5" in result.upper()
    assert result.upper().count("LIMIT") == 1


def test_add_limit_adds_outer_limit_when_only_subquery_has_one():
    sql = "SELECT * FROM (SELECT * FROM orders LIMIT 10) sub"
    result = _add_limit(sql, 100)
    assert "LIMIT 100" in result.upper()
    assert "LIMIT 10" in result.upper()


def test_add_limit_handles_unparseable_sql():
    result = _add_limit("NOT VALID SQL !!!@#", 50)
    assert "LIMIT 50" in result.upper()


# ── execute_and_capture ───────────────────────────────────────────────────────

def _make_exec_conn(sfqid="test-qid-123"):
    cur = MagicMock()
    cur.sfqid = sfqid
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


def test_execute_and_capture_returns_query_id():
    conn, _ = _make_exec_conn("returned-qid")
    result = execute_and_capture(conn, "SELECT id FROM orders", limit=100)
    assert result == "returned-qid"


def test_execute_and_capture_adds_limit():
    conn, cur = _make_exec_conn()
    execute_and_capture(conn, "SELECT * FROM orders", limit=50)
    called_sql = cur.execute.call_args[0][0]
    assert "50" in called_sql


def test_execute_and_capture_rejects_non_select():
    conn, _ = _make_exec_conn()
    with pytest.raises(ValueError, match="Only SELECT"):
        execute_and_capture(conn, "INSERT INTO orders VALUES (1)", limit=100)


def test_execute_and_capture_rejects_update():
    conn, _ = _make_exec_conn()
    with pytest.raises(ValueError, match="Only SELECT"):
        execute_and_capture(conn, "UPDATE orders SET status='done'", limit=100)


# ── _compute_improvement ──────────────────────────────────────────────────────

def _make_kpis(**kwargs):
    defaults = dict(
        query_id="q", elapsed_ms=None, bytes_scanned=None,
        bytes_spilled_local=None, bytes_spilled_remote=None,
        partitions_scanned=None, partitions_total=None,
        rows_produced=None, credits=None, source="live",
    )
    defaults.update(kwargs)
    return QueryKPIs(**defaults)


def test_compute_improvement_negative_pct_when_post_lower():
    pre = _make_kpis(elapsed_ms=2000)
    post = _make_kpis(elapsed_ms=1000)
    result = _compute_improvement(pre, post)
    assert result["elapsed_ms"] == -50.0


def test_compute_improvement_skips_none_values():
    pre = _make_kpis(elapsed_ms=None, bytes_scanned=1000)
    post = _make_kpis(elapsed_ms=None, bytes_scanned=500)
    result = _compute_improvement(pre, post)
    assert "elapsed_ms" not in result
    assert result["bytes_scanned"] == -50.0


def test_compute_improvement_skips_zero_pre():
    pre = _make_kpis(elapsed_ms=0)
    post = _make_kpis(elapsed_ms=100)
    result = _compute_improvement(pre, post)
    assert "elapsed_ms" not in result


# ── build_comparison ──────────────────────────────────────────────────────────

def _kpis_fixture(query_id, elapsed_ms, source):
    return QueryKPIs(
        query_id=query_id, elapsed_ms=elapsed_ms, bytes_scanned=None,
        bytes_spilled_local=None, bytes_spilled_remote=None,
        partitions_scanned=None, partitions_total=None,
        rows_produced=None, credits=None, source=source,
    )


def test_build_comparison_uses_history_when_found():
    pre_kpis = _kpis_fixture("hist-id", 3000, "history")
    post_kpis = _kpis_fixture("live-id", 1500, "live")

    conn = MagicMock()
    with patch("backend.agents.query_runner.find_recent_query_run", return_value="hist-id") as mock_find, \
         patch("backend.agents.query_runner.fetch_query_kpis") as mock_kpis, \
         patch("backend.agents.query_runner.execute_and_capture", return_value="live-id") as mock_exec:
        mock_kpis.side_effect = [pre_kpis, post_kpis]
        result = build_comparison(conn, "SELECT * FROM orders", "SELECT id FROM orders")

    assert isinstance(result, ComparisonResult)
    assert result.pre.source == "history"
    assert result.post.source == "live"
    mock_find.assert_called_once()
    mock_exec.assert_called_once()  # original not re-executed when found in history


def test_build_comparison_executes_original_when_not_in_history():
    pre_kpis = _kpis_fixture("exec-pre-id", 3000, "live")
    post_kpis = _kpis_fixture("exec-post-id", 1500, "live")

    conn = MagicMock()
    with patch("backend.agents.query_runner.find_recent_query_run", return_value=None), \
         patch("backend.agents.query_runner.fetch_query_kpis") as mock_kpis, \
         patch("backend.agents.query_runner.execute_and_capture") as mock_exec:
        mock_exec.side_effect = ["exec-pre-id", "exec-post-id"]
        mock_kpis.side_effect = [pre_kpis, post_kpis]
        result = build_comparison(conn, "SELECT * FROM orders", "SELECT id FROM orders")

    assert result.pre.source == "live"
    assert mock_exec.call_count == 2  # both original and optimized executed
