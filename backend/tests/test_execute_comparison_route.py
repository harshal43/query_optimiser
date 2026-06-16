import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.models.kpi_models import QueryKPIs, ComparisonResult


@pytest.fixture
def client():
    return TestClient(app)


def _make_kpis(query_id, elapsed_ms, source):
    return QueryKPIs(
        query_id=query_id, elapsed_ms=elapsed_ms, bytes_scanned=None,
        bytes_spilled_local=None, bytes_spilled_remote=None,
        partitions_scanned=None, partitions_total=None,
        rows_produced=None, credits=None, source=source,
    )


def test_execute_comparison_returns_200_with_structure(client):
    pre = _make_kpis("pre-id", 3000, "history")
    post = _make_kpis("post-id", 1500, "live")
    comparison = ComparisonResult(pre=pre, post=post, improvement={"elapsed_ms": -50.0})

    with patch("backend.data.snowflake_connector.is_connected", return_value=True), \
         patch("backend.data.snowflake_connector._conn", MagicMock()), \
         patch("backend.api.routes.build_comparison", return_value=comparison):
        res = client.post("/api/execute-comparison", json={
            "original_query": "SELECT * FROM orders",
            "optimized_query": "SELECT id, status FROM orders WHERE status = 'active'",
        })

    assert res.status_code == 200
    data = res.json()
    assert data["pre"]["query_id"] == "pre-id"
    assert data["post"]["query_id"] == "post-id"
    assert data["improvement"]["elapsed_ms"] == -50.0


def test_execute_comparison_503_when_not_connected(client):
    with patch("backend.data.snowflake_connector.is_connected", return_value=False):
        res = client.post("/api/execute-comparison", json={
            "original_query": "SELECT * FROM orders",
            "optimized_query": "SELECT id FROM orders",
        })
    assert res.status_code == 503


def test_execute_comparison_400_on_value_error(client):
    with patch("backend.data.snowflake_connector.is_connected", return_value=True), \
         patch("backend.data.snowflake_connector._conn", MagicMock()), \
         patch("backend.api.routes.build_comparison", side_effect=ValueError("Only SELECT")):
        res = client.post("/api/execute-comparison", json={
            "original_query": "INSERT INTO t VALUES (1)",
            "optimized_query": "SELECT 1",
        })
    assert res.status_code == 400
    assert "Only SELECT" in res.json()["detail"]
