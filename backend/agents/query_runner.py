from __future__ import annotations

from typing import Optional

import sqlglot
from sqlglot import exp

from ..models.kpi_models import QueryKPIs, ComparisonResult
from .snowflake_context import find_recent_query_run, fetch_query_kpis


def _add_limit(sql: str, limit: int = 100) -> str:
    try:
        tree = sqlglot.parse_one(sql, dialect="snowflake")
    except Exception:
        return f"{sql.rstrip().rstrip(';')}\nLIMIT {limit}"

    # Check only outermost LIMIT — args.get does not recurse into subqueries
    if tree.args.get("limit") is not None:
        return sql

    tree.set("limit", exp.Limit(expression=exp.Literal.number(limit)))
    return tree.sql(dialect="snowflake")


def execute_and_capture(conn, sql: str, limit: int = 100) -> str:
    """
    Execute sql on conn with a LIMIT guard and return the Snowflake query ID.
    Only SELECT statements are allowed; raises ValueError otherwise.
    """
    try:
        tree = sqlglot.parse_one(sql, dialect="snowflake")
        if not isinstance(tree, exp.Select):
            raise ValueError(
                f"Only SELECT statements are allowed in sandbox execution, got: {type(tree).__name__}"
            )
    except sqlglot.errors.ParseError as exc:
        raise ValueError(f"SQL parse error: {exc}") from exc

    import snowflake.connector

    limited_sql = _add_limit(sql, limit)
    cur = conn.cursor(snowflake.connector.DictCursor)
    cur.execute(limited_sql)
    cur.fetchall()  # consume results so execution completes
    query_id: str = cur.sfqid
    if not query_id:
        raise RuntimeError("Snowflake did not return a query ID after execution")
    return query_id


def _compute_improvement(pre: QueryKPIs, post: QueryKPIs) -> dict[str, float]:
    metrics = [
        "elapsed_ms",
        "bytes_scanned",
        "bytes_spilled_local",
        "bytes_spilled_remote",
        "partitions_scanned",
        "credits",
    ]
    result: dict[str, float] = {}
    for metric in metrics:
        pre_val = getattr(pre, metric)
        post_val = getattr(post, metric)
        if pre_val is None or post_val is None or pre_val == 0:
            continue
        pct = round((post_val - pre_val) / pre_val * 100, 1)
        result[metric] = pct
    return result


def build_comparison(conn, original_sql: str, optimized_sql: str) -> ComparisonResult:
    # Step 1: look for original in history to avoid re-running it
    pre_id = find_recent_query_run(conn, original_sql)
    if pre_id:
        pre_kpis = fetch_query_kpis(conn, pre_id, source="history")
    else:
        pre_id = execute_and_capture(conn, original_sql)
        pre_kpis = fetch_query_kpis(conn, pre_id, source="live")

    # Step 2: always execute optimized to get fresh numbers
    post_id = execute_and_capture(conn, optimized_sql)
    post_kpis = fetch_query_kpis(conn, post_id, source="live")

    return ComparisonResult(
        pre=pre_kpis,
        post=post_kpis,
        improvement=_compute_improvement(pre_kpis, post_kpis),
    )
