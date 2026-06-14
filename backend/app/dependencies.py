from __future__ import annotations
import asyncpg
import faiss
from app.db.connection import get_pool
from app.vector.index import get_index


async def db_pool() -> asyncpg.Pool:
    return get_pool()


def faiss_index(name: str) -> faiss.Index:
    return get_index(name)
