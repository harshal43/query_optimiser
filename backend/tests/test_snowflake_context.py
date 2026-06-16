import pytest
from backend.agents.snowflake_context import (
    _extract_tables,
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
