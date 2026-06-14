from __future__ import annotations
import asyncpg
from app.config import settings

_pool: asyncpg.Pool | None = None


async def open_pool() -> None:
    global _pool
    dsn = settings.database_url.replace("+asyncpg", "")
    _pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10, command_timeout=30)


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialized — call open_pool() first")
    return _pool
