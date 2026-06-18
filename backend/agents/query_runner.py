from __future__ import annotations

import logging
import time
from typing import Optional

import sqlglot
from sqlglot import exp

from ..models.kpi_models import QueryKPIs, ComparisonResult
from .snowflake_context import find_recent_query_run, fetch_query_kpis, _resolve_database, _resolve_schema, _IDENT_RE

logger = logging.getLogger(__name__)


def _add_limit(sql: str, limit: int = 100) -> str:
    """Add a LIMIT clause to a SELECT query safely.

    Uses sqlglot AST manipulation as primary method, with string-based
    fallback to avoid corrupting complex SQL.
    """
    # First, try sqlglot approach
    try:
        tree = sqlglot.parse_one(sql, dialect="snowflake")
    except Exception:
        # Fallback: simple string append
        return f"{sql.rstrip().rstrip(';')}\nLIMIT {limit}"

    # For CTEs, the outermost SELECT is tree.this; for plain SELECT it is tree itself
    select_node = tree.this if isinstance(tree, exp.With) else tree

    # Handle UNION / INTERSECT / EXCEPT — limit applies to the whole result set
    # In these cases, we need to wrap the whole thing in a subquery
    if isinstance(select_node, (exp.Union, exp.Intersect, exp.Except)):
        wrapped = f"SELECT * FROM ({sql.rstrip().rstrip(';')}) AS _limited LIMIT {limit}"
        return wrapped

    # Check only outermost LIMIT
    if select_node.args.get("limit") is not None:
        return sql

    # Add LIMIT to the outermost SELECT
    try:
        select_node.set("limit", exp.Limit(expression=exp.Literal.number(limit)))
        return tree.sql(dialect="snowflake")
    except Exception:
        # Fallback if AST manipulation fails
        return f"{sql.rstrip().rstrip(';')} LIMIT {limit}"


def execute_and_capture(conn, sql: str, limit: int = 100) -> str:
    """
    Execute sql on conn with a LIMIT guard and return the Snowflake query ID.
    Only SELECT statements (including CTEs) are allowed; raises ValueError otherwise.

    FIXED:
    - Validates SQL before adding LIMIT
    - Sets proper database/schema context (resolves from session if needed)
    - Wraps execution in try/except with meaningful error messages
    - Handles UNION/INTERSECT/EXCEPT correctly
    - Uses LAST_QUERY_ID() as fallback for sfqid
    """
    import snowflake.connector
    from ..data import snowflake_connector as sc

    # Step 1: Validate that this is a SELECT statement
    try:
        tree = sqlglot.parse_one(sql, dialect="snowflake")
        is_select = isinstance(tree, exp.Select) or (
            isinstance(tree, exp.With) and isinstance(tree.this, exp.Select)
        ) or isinstance(tree, (exp.Union, exp.Intersect, exp.Except))
        if not is_select:
            raise ValueError(
                f"Only SELECT statements are allowed in sandbox execution, got: {type(tree).__name__}"
            )
    except sqlglot.errors.ParseError as exc:
        raise ValueError(f"SQL parse error: {exc}") from exc

    # Step 2: Add LIMIT guard
    limited_sql = _add_limit(sql, limit)
    logger.debug("Original SQL:\n%s", sql)
    logger.debug("Limited SQL:\n%s", limited_sql)

    # Step 3: Set database/schema context using a separate cursor
    creds = sc._creds or {}
    db = _resolve_database(conn, creds.get("database") or "")
    schema = _resolve_schema(conn, creds.get("schema_name") or "")

    logger.debug("Resolved context | db=%s | schema=%s", db, schema)

    # Use standard cursor for context setting (DictCursor not needed here)
    ctx_cur = conn.cursor()
    try:
        if db and _IDENT_RE.match(db):
            ctx_cur.execute(f"USE DATABASE {db}")
        if schema and _IDENT_RE.match(schema):
            ctx_cur.execute(f"USE SCHEMA {db}.{schema}" if db else f"USE SCHEMA {schema}")
    except Exception as exc:
        logger.warning("Failed to set database/schema context: %s", exc)
    finally:
        ctx_cur.close()

    # Step 4: Execute with DictCursor for result consumption
    cur = conn.cursor(snowflake.connector.DictCursor)

    try:
        cur.execute(limited_sql)
    except snowflake.connector.errors.ProgrammingError as exc:
        err_msg = str(exc)
        logger.error("Snowflake execution error: %s", err_msg)

        if "does not exist" in err_msg.lower():
            raise ValueError(
                f"Query execution failed: Table or object does not exist. "
                f"Ensure the query references valid tables in database '{db}', schema '{schema}'. "
                f"Original error: {err_msg}"
            ) from exc
        elif "permission" in err_msg.lower() or "privilege" in err_msg.lower():
            raise ValueError(
                f"Query execution failed: Insufficient privileges. "
                f"Check that your Snowflake role has SELECT permission. "
                f"Original error: {err_msg}"
            ) from exc
        elif "syntax error" in err_msg.lower():
            raise ValueError(
                f"Query execution failed: SQL syntax error. "
                f"The optimized query may have been corrupted. "
                f"Original error: {err_msg}"
            ) from exc
        else:
            raise ValueError(f"Query execution failed: {err_msg}") from exc
    except Exception as exc:
        logger.error("Unexpected execution error: %s", exc)
        raise ValueError(f"Query execution failed unexpectedly: {exc}") from exc

    # Step 5: Consume results and get query ID
    try:
        cur.fetchall()  # consume results so execution completes
    except Exception as exc:
        logger.warning("Failed to fetch results (query may have no rows): %s", exc)

    # Step 6: Get query ID — try sfqid first, then LAST_QUERY_ID() fallback
    query_id: Optional[str] = None

    # Method 1: cursor.sfqid
    try:
        query_id = cur.sfqid
        if query_id:
            logger.info("Got query ID from cursor.sfqid: %s", query_id)
    except Exception as exc:
        logger.warning("cursor.sfqid failed: %s", exc)

    # Method 2: LAST_QUERY_ID() fallback
    if not query_id:
        try:
            id_cur = conn.cursor()
            id_cur.execute("SELECT LAST_QUERY_ID() AS QID")
            row = id_cur.fetchone()
            if row:
                query_id = str(row[0]) if isinstance(row, tuple) else str(row.get("QID", ""))
                if query_id and query_id.lower() != "none":
                    logger.info("Got query ID from LAST_QUERY_ID(): %s", query_id)
            id_cur.close()
        except Exception as exc:
            logger.warning("LAST_QUERY_ID() fallback failed: %s", exc)

    cur.close()

    if not query_id or query_id.lower() == "none":
        raise RuntimeError(
            "Snowflake did not return a query ID after execution. "
            "This may indicate the query failed silently or the connection was lost."
        )

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


def _fetch_kpis_with_retry(conn, query_id: str, source: str = "live", max_retries: int = 5, delay: float = 1.0) -> QueryKPIs:
    """Fetch query KPIs with retry logic to handle QUERY_HISTORY latency.

    Snowflake's INFORMATION_SCHEMA.QUERY_HISTORY can have a few seconds of delay
    before newly executed queries appear.
    """
    for attempt in range(max_retries):
        kpis = fetch_query_kpis(conn, query_id, source=source)
        if kpis.error is None:
            return kpis

        logger.debug(
            "KPI fetch attempt %d/%d failed for %s: %s",
            attempt + 1, max_retries, query_id, kpis.error
        )

        if attempt < max_retries - 1:
            time.sleep(delay * (2 ** attempt))  # exponential backoff: 1s, 2s, 4s, 8s...

    logger.warning("KPI fetch failed after %d retries for query %s", max_retries, query_id)
    return kpis


def build_comparison(conn, original_sql: str, optimized_sql: str) -> ComparisonResult:
    """
    Execute both original and optimized queries, fetch their KPIs, and compare.

    FIXED:
    - Gracefully handles failures in original query execution
    - Retries KPI fetching to handle QUERY_HISTORY latency
    - Includes query IDs in the result for frontend debugging
    - Better error messages for each failure mode
    """
    logger.info("Building comparison | original_len=%d | optimized_len=%d", 
                len(original_sql), len(optimized_sql))

    # ── Step 1: Original query ──
    pre_id: Optional[str] = None
    pre_kpis: QueryKPIs
    pre_source = "history"

    # Try to find in history first
    try:
        pre_id = find_recent_query_run(conn, original_sql)
        if pre_id:
            logger.info("Found original query in history | query_id=%s", pre_id)
            pre_kpis = _fetch_kpis_with_retry(conn, pre_id, source="history", max_retries=3)
        else:
            raise RuntimeError("Not found in history")
    except Exception as exc:
        logger.info("Original query not in history, executing live: %s", exc)
        try:
            pre_id = execute_and_capture(conn, original_sql)
            pre_kpis = _fetch_kpis_with_retry(conn, pre_id, source="live")
            pre_source = "live"
        except Exception as exec_exc:
            logger.error("Failed to execute original query: %s", exec_exc)
            # Create a fallback KPIs with error info
            pre_kpis = QueryKPIs(
                query_id="error",
                elapsed_ms=None, bytes_scanned=None,
                bytes_spilled_local=None, bytes_spilled_remote=None,
                partitions_scanned=None, partitions_total=None,
                rows_produced=None, credits=None,
                source="error",
                error=f"Original query execution failed: {exec_exc}",
            )

    # ── Step 2: Optimized query ──
    post_id: Optional[str] = None
    post_kpis: QueryKPIs

    try:
        post_id = execute_and_capture(conn, optimized_sql)
        post_kpis = _fetch_kpis_with_retry(conn, post_id, source="live")
    except Exception as exc:
        logger.error("Failed to execute optimized query: %s", exc)
        post_kpis = QueryKPIs(
            query_id="error",
            elapsed_ms=None, bytes_scanned=None,
            bytes_spilled_local=None, bytes_spilled_remote=None,
            partitions_scanned=None, partitions_total=None,
            rows_produced=None, credits=None,
            source="error",
            error=f"Optimized query execution failed: {exc}",
        )

    # ── Step 3: Compute improvement ──
    improvement = _compute_improvement(pre_kpis, post_kpis)

    # ── Step 4: Build result with query IDs for frontend ──
    result = ComparisonResult(
        pre=pre_kpis,
        post=post_kpis,
        improvement=improvement,
    )

    # Attach query IDs as extra attributes (not in dataclass, but accessible)
    result.pre_query_id = pre_id
    result.post_query_id = post_id
    result.pre_source = pre_source

    logger.info(
        "Comparison complete | pre_id=%s | post_id=%s | improvement=%s",
        pre_id, post_id, improvement
    )

    return result