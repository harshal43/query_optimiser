from backend.models.kpi_models import QueryKPIs, ComparisonResult


def test_query_kpis_construction():
    kpis = QueryKPIs(
        query_id="abc-123",
        elapsed_ms=2000,
        bytes_scanned=1_000_000,
        bytes_spilled_local=0,
        bytes_spilled_remote=0,
        partitions_scanned=5,
        partitions_total=10,
        rows_produced=100,
        credits=0.001,
        source="history",
    )
    assert kpis.query_id == "abc-123"
    assert kpis.elapsed_ms == 2000
    assert kpis.source == "history"
    assert kpis.error is None


def test_query_kpis_with_error():
    kpis = QueryKPIs(
        query_id="xyz",
        elapsed_ms=None,
        bytes_scanned=None,
        bytes_spilled_local=None,
        bytes_spilled_remote=None,
        partitions_scanned=None,
        partitions_total=None,
        rows_produced=None,
        credits=None,
        source="live",
        error="Query not found",
    )
    assert kpis.error == "Query not found"
    assert kpis.elapsed_ms is None


def test_comparison_result_construction():
    pre = QueryKPIs(
        query_id="pre", elapsed_ms=3000, bytes_scanned=500_000,
        bytes_spilled_local=None, bytes_spilled_remote=None,
        partitions_scanned=10, partitions_total=20,
        rows_produced=200, credits=0.002, source="history",
    )
    post = QueryKPIs(
        query_id="post", elapsed_ms=1500, bytes_scanned=250_000,
        bytes_spilled_local=None, bytes_spilled_remote=None,
        partitions_scanned=5, partitions_total=20,
        rows_produced=200, credits=0.001, source="live",
    )
    result = ComparisonResult(pre=pre, post=post, improvement={"elapsed_ms": -50.0})
    assert result.improvement["elapsed_ms"] == -50.0
    assert result.pre.query_id == "pre"
    assert result.post.query_id == "post"
