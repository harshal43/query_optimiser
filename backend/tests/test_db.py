from __future__ import annotations
import pytest
from app.db import connection as c


@pytest.mark.asyncio
async def test_pool_opens_and_queries():
    await c.open_pool()
    pool = c.get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
    assert result == 1
    await c.close_pool()


def test_get_pool_raises_before_open():
    c._pool = None
    with pytest.raises(RuntimeError, match="DB pool not initialized"):
        c.get_pool()


@pytest.mark.asyncio
async def test_pool_closes_cleanly():
    await c.open_pool()
    await c.close_pool()
    assert c._pool is None


@pytest.mark.asyncio
async def test_all_seven_tables_exist():
    await c.open_pool()
    pool = c.get_pool()
    tables = ["queries", "optimizations", "feedback", "teams",
              "techniques", "ab_tests", "audit_log"]
    async with pool.acquire() as conn:
        for table in tables:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name=$1",
                table,
            )
            assert count == 1, f"Table '{table}' not found in DB"
    await c.close_pool()
