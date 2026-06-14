from __future__ import annotations
import pytest
from httpx import AsyncClient


async def test_list_queries_returns_shape(client: AsyncClient):
    r = await client.get("/api/queries")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["items"], list)


async def test_list_queries_limit(client: AsyncClient):
    r = await client.get("/api/queries?limit=2&offset=0")
    assert r.status_code == 200
    assert len(r.json()["items"]) <= 2


async def test_list_queries_severity_filter(client: AsyncClient):
    r = await client.get("/api/queries?severity=critical")
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["severity"] == "critical"


async def test_list_queries_status_filter(client: AsyncClient):
    r = await client.get("/api/queries?status=pending_review")
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["status"] == "pending_review"


async def test_get_query_not_found(client: AsyncClient):
    r = await client.get("/api/queries/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


async def test_get_query_by_id(client: AsyncClient):
    list_r = await client.get("/api/queries?limit=1")
    items = list_r.json()["items"]
    if not items:
        pytest.skip("No queries seeded yet")
    qid = items[0]["query_id"]
    r = await client.get(f"/api/queries/{qid}")
    assert r.status_code == 200
    assert r.json()["query_id"] == qid
    assert "query_text" in r.json()
