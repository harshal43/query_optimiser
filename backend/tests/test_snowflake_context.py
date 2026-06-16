import time
import pytest
from unittest.mock import MagicMock, patch

import backend.agents.snowflake_context as sc_module
from backend.agents.snowflake_context import (
    _extract_tables,
    _fetch_table_meta,
    fetch_snowflake_context,
    build_context_block,
    SnowflakeContext,
    TableMeta,
    ColumnMeta,
)


def test_extract_tables_simple():
    result = _extract_tables("SELECT * FROM orders WHERE id = 1")
    assert result == ["ORDERS"]


def test_extract_tables_join():
    sql = "SELECT o.id FROM orders o JOIN customers c ON o.customer_id = c.id"
    assert set(_extract_tables(sql)) == {"ORDERS", "CUSTOMERS"}


def test_extract_tables_cte():
    sql = """
    WITH recent AS (SELECT * FROM orders WHERE created_at > '2024-01-01')
    SELECT * FROM recent JOIN customers c ON recent.customer_id = c.id
    """
    result = set(_extract_tables(sql))
    assert "ORDERS" in result
    assert "CUSTOMERS" in result


def test_extract_tables_parse_failure_returns_empty_list():
    result = _extract_tables("NOT VALID SQL !!!@#$%")
    assert result == []


def test_snowflake_context_defaults():
    ctx = SnowflakeContext(available=False, tables={})
    assert ctx.available is False
    assert ctx.tables == {}
    assert ctx.fetch_errors == []


def test_table_meta_fields():
    meta = TableMeta(columns=[], clustering_key=None, clustering_depth=None, row_count=None)
    assert meta.columns == []
    assert meta.clustering_key is None
    assert meta.clustering_depth is None
    assert meta.row_count is None


def test_column_meta_fields():
    col = ColumnMeta(name="ORDER_ID", data_type="NUMBER", is_nullable=False, constraints=["PRIMARY KEY"])
    assert col.name == "ORDER_ID"
    assert col.is_nullable is False
    assert "PRIMARY KEY" in col.constraints


# ── _fetch_table_meta helpers ─────────────────────────────────────────────────

def _make_mock_conn(col_rows, constraint_rows, table_row, depth_row):
    """Build a mock snowflake connection whose cursor replays the given rows."""
    cursor = MagicMock()
    cursor.fetchall.side_effect = [col_rows, constraint_rows]
    cursor.fetchone.side_effect = [table_row, depth_row]
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn


def test_fetch_table_meta_populates_columns():
    col_rows = [
        {"COLUMN_NAME": "ORDER_ID", "DATA_TYPE": "NUMBER",  "IS_NULLABLE": "NO"},
        {"COLUMN_NAME": "STATUS",   "DATA_TYPE": "VARCHAR", "IS_NULLABLE": "YES"},
    ]
    constraint_rows = [{"COLUMN_NAME": "ORDER_ID", "CONSTRAINT_TYPE": "PRIMARY KEY"}]
    table_row = {"CLUSTERING_KEY": "(CREATED_AT)", "ROW_COUNT": 1_000_000}
    depth_row  = {"DEPTH": 0.85}

    conn = _make_mock_conn(col_rows, constraint_rows, table_row, depth_row)
    meta = _fetch_table_meta(conn, "MYDB", "PUBLIC", "ORDERS")

    assert len(meta.columns) == 2
    assert meta.columns[0].name == "ORDER_ID"
    assert meta.columns[0].data_type == "NUMBER"
    assert meta.columns[0].is_nullable is False
    assert meta.columns[0].constraints == ["PRIMARY KEY"]
    assert meta.columns[1].name == "STATUS"
    assert meta.columns[1].is_nullable is True
    assert meta.clustering_key == "(CREATED_AT)"
    assert meta.row_count == 1_000_000
    assert meta.clustering_depth == pytest.approx(0.85)


def test_fetch_table_meta_null_clustering_depth():
    col_rows = [{"COLUMN_NAME": "ID", "DATA_TYPE": "NUMBER", "IS_NULLABLE": "NO"}]
    table_row = {"CLUSTERING_KEY": None, "ROW_COUNT": 500}
    conn = _make_mock_conn(col_rows, [], table_row, None)
    meta = _fetch_table_meta(conn, "MYDB", "PUBLIC", "SMALL")
    assert meta.clustering_depth is None


def test_fetch_table_meta_returns_none_for_missing_table():
    conn = _make_mock_conn([], [], None, None)
    result = _fetch_table_meta(conn, "MYDB", "PUBLIC", "GHOST")
    assert result is None


# ── fetch_snowflake_context ───────────────────────────────────────────────────

def test_returns_unavailable_when_not_connected():
    with patch("backend.data.snowflake_connector.is_connected", return_value=False):
        ctx = fetch_snowflake_context("SELECT * FROM orders")
    assert ctx.available is False
    assert ctx.tables == {}
    assert ctx.fetch_errors == []


def test_missing_table_logged_to_fetch_errors():
    cursor = MagicMock()
    cursor.fetchall.return_value = []   # empty = table not in schema
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = cursor

    with patch("backend.data.snowflake_connector.is_connected", return_value=True), \
         patch("backend.data.snowflake_connector._conn", mock_conn), \
         patch("backend.data.snowflake_connector._creds", {"database": "DB", "schema_name": "PUBLIC"}):
        ctx = fetch_snowflake_context("SELECT * FROM ghost_table")

    assert ctx.available is True
    assert "GHOST_TABLE" not in ctx.tables
    # Fix 6: error message now says "Could not fetch metadata for table:"
    assert any("Could not fetch metadata for table" in e and "GHOST_TABLE" in e
               for e in ctx.fetch_errors)


def test_cache_prevents_duplicate_fetch():
    sc_module._cache.clear()
    sc_module._cache_connection_key = ""  # reset so first call sets it

    col_rows = [{"COLUMN_NAME": "ID", "DATA_TYPE": "NUMBER", "IS_NULLABLE": "NO"}]
    cursor = MagicMock()
    cursor.fetchall.side_effect = [col_rows, []]           # columns, constraints
    cursor.fetchone.side_effect = [
        {"CLUSTERING_KEY": None, "ROW_COUNT": 100}, None  # table row, depth
    ]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = cursor

    with patch("backend.data.snowflake_connector.is_connected", return_value=True), \
         patch("backend.data.snowflake_connector._conn", mock_conn), \
         patch("backend.data.snowflake_connector._creds", {"database": "DB", "schema_name": "PUBLIC"}):
        fetch_snowflake_context("SELECT * FROM orders")
        fetch_snowflake_context("SELECT * FROM orders")  # cache hit

    # cursor was created only once (only one _fetch_table_meta call)
    assert mock_conn.cursor.call_count == 1


def test_cache_expires_after_ttl():
    sc_module._cache.clear()
    sc_module._cache_connection_key = "DB.PUBLIC"  # match the creds used below

    # Pre-seed an expired entry using the db-qualified key (Fix 2)
    stale_meta = TableMeta(columns=[], clustering_key=None, clustering_depth=None, row_count=None)
    expired_ts = time.monotonic() - sc_module._TTL_SECONDS - 1
    sc_module._cache["DB.PUBLIC.ORDERS"] = (stale_meta, expired_ts)

    col_rows = [{"COLUMN_NAME": "ID", "DATA_TYPE": "NUMBER", "IS_NULLABLE": "NO"}]
    cursor = MagicMock()
    cursor.fetchall.side_effect = [col_rows, []]
    cursor.fetchone.side_effect = [{"CLUSTERING_KEY": None, "ROW_COUNT": 50}, None]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = cursor

    with patch("backend.data.snowflake_connector.is_connected", return_value=True), \
         patch("backend.data.snowflake_connector._conn", mock_conn), \
         patch("backend.data.snowflake_connector._creds", {"database": "DB", "schema_name": "PUBLIC"}):
        fetch_snowflake_context("SELECT * FROM orders")

    # Expired entry should have been re-fetched
    assert mock_conn.cursor.call_count >= 1


# ── Fix 1: TOCTOU — conn becomes None after is_connected() ───────────────────

def test_returns_unavailable_when_conn_is_none_after_is_connected():
    """is_connected() returns True but _conn is None (race with disconnect)."""
    with patch("backend.data.snowflake_connector.is_connected", return_value=True), \
         patch("backend.data.snowflake_connector._conn", None), \
         patch("backend.data.snowflake_connector._creds", {"database": "DB", "schema_name": "PUBLIC"}):
        ctx = fetch_snowflake_context("SELECT * FROM orders")

    assert ctx.available is False
    assert ctx.tables == {}
    assert ctx.fetch_errors == []


# ── Fix 3: cache cleared when db/schema changes ───────────────────────────────

def test_cache_cleared_on_db_schema_change():
    """Switching to a different database clears the stale cache."""
    sc_module._cache.clear()
    sc_module._cache_connection_key = "OLD_DB.PUBLIC"

    # Pre-seed a fresh (non-expired) entry under the old connection key
    stale_meta = TableMeta(columns=[], clustering_key=None, clustering_depth=None, row_count=None)
    sc_module._cache["OLD_DB.PUBLIC.ORDERS"] = (stale_meta, time.monotonic())

    col_rows = [{"COLUMN_NAME": "ID", "DATA_TYPE": "NUMBER", "IS_NULLABLE": "NO"}]
    cursor = MagicMock()
    cursor.fetchall.side_effect = [col_rows, []]
    cursor.fetchone.side_effect = [{"CLUSTERING_KEY": None, "ROW_COUNT": 10}, None]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = cursor

    # Connect with a NEW database — cache should be cleared, fresh fetch performed
    with patch("backend.data.snowflake_connector.is_connected", return_value=True), \
         patch("backend.data.snowflake_connector._conn", mock_conn), \
         patch("backend.data.snowflake_connector._creds", {"database": "NEW_DB", "schema_name": "PUBLIC"}):
        ctx = fetch_snowflake_context("SELECT * FROM orders")

    # Cache was cleared, so a real fetch happened
    assert mock_conn.cursor.call_count >= 1
    assert sc_module._cache_connection_key == "NEW_DB.PUBLIC"
    assert ctx.available is True
    assert "ORDERS" in ctx.tables


# ── build_context_block ───────────────────────────────────────────────────────

def _make_context(tables: dict) -> SnowflakeContext:
    return SnowflakeContext(available=True, tables=tables)


def test_build_context_block_empty_when_not_available():
    ctx = SnowflakeContext(available=False, tables={})
    assert build_context_block(ctx) == ""


def test_build_context_block_empty_when_no_tables():
    ctx = SnowflakeContext(available=True, tables={})
    assert build_context_block(ctx) == ""


def test_build_context_block_contains_metadata():
    meta = TableMeta(
        columns=[
            ColumnMeta("ORDER_ID", "NUMBER",  False, ["PRIMARY KEY"]),
            ColumnMeta("STATUS",   "VARCHAR", True,  []),
        ],
        clustering_key="(CREATED_AT)",
        clustering_depth=0.83,
        row_count=1_000_000,
    )
    block = build_context_block(_make_context({"ORDERS": meta}))
    assert "ORDERS" in block
    assert "ORDER_ID" in block
    assert "NUMBER" in block
    assert "PRIMARY KEY" in block
    assert "(CREATED_AT)" in block
    assert "0.83" in block
    assert "1,000,000" in block
    assert "NOT NULL" in block
    assert "nullable" in block


def test_build_context_block_none_clustering_key():
    meta = TableMeta(columns=[], clustering_key=None, clustering_depth=None, row_count=None)
    block = build_context_block(_make_context({"SMALL": meta}))
    assert "none" in block
    assert "SMALL" in block


def test_build_context_block_high_depth_warns():
    meta = TableMeta(columns=[], clustering_key="(X)", clustering_depth=0.9, row_count=None)
    block = build_context_block(_make_context({"BIG": meta}))
    assert "poor clustering" in block
    assert "micro-partition" in block


def test_build_context_block_depth_at_boundary_is_well_clustered():
    meta = TableMeta(columns=[], clustering_key="(X)", clustering_depth=0.7, row_count=None)
    block = build_context_block(_make_context({"T": meta}))
    assert "well clustered" in block


def test_build_context_block_just_above_boundary_warns():
    meta = TableMeta(columns=[], clustering_key="(X)", clustering_depth=0.71, row_count=None)
    block = build_context_block(_make_context({"T": meta}))
    assert "poor clustering" in block
