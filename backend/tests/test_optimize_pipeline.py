from __future__ import annotations
import pytest
from httpx import AsyncClient


async def test_optimize_unknown_query(client: AsyncClient):
    r = await client.post("/api/optimizations", json={"query_id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 404


async def test_optimize_creates_optimization(client: AsyncClient):
    queries_r = await client.get("/api/queries?limit=1")
    items = queries_r.json()["items"]
    if not items:
        pytest.skip("No queries seeded")
    qid = items[0]["query_id"]
    r = await client.post("/api/optimizations", json={"query_id": qid})
    assert r.status_code == 200
    data = r.json()
    assert "optimization_id" in data
    assert data["status"] == "pending_review"


async def test_get_optimization(client: AsyncClient):
    queries_r = await client.get("/api/queries?limit=1")
    items = queries_r.json()["items"]
    if not items:
        pytest.skip("No queries seeded")
    qid = items[0]["query_id"]
    create_r = await client.post("/api/optimizations", json={"query_id": qid})
    opt_id = create_r.json()["optimization_id"]
    r = await client.get(f"/api/optimizations/{opt_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["optimization_id"] == opt_id
    assert "diagnosis" in data
    assert "variants" in data
    assert "cost_predictions" in data
    assert "validation_results" in data


async def test_optimization_has_variants(client: AsyncClient):
    queries_r = await client.get("/api/queries?severity=critical&limit=1")
    items = queries_r.json()["items"]
    if not items:
        pytest.skip("No critical queries")
    qid = items[0]["query_id"]
    create_r = await client.post("/api/optimizations", json={"query_id": qid})
    opt_id = create_r.json()["optimization_id"]
    r = await client.get(f"/api/optimizations/{opt_id}")
    data = r.json()
    assert len(data["variants"]) >= 1
    assert data["variants"][0]["sql"] != ""


async def test_approve_optimization(client: AsyncClient):
    queries_r = await client.get("/api/queries?limit=1")
    items = queries_r.json()["items"]
    if not items:
        pytest.skip("No queries seeded")
    qid = items[0]["query_id"]
    create_r = await client.post("/api/optimizations", json={"query_id": qid})
    opt_id = create_r.json()["optimization_id"]
    r = await client.post(f"/api/optimizations/{opt_id}/approve", json={"selected_variant": "v1"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


async def test_reject_optimization(client: AsyncClient):
    queries_r = await client.get("/api/queries?limit=1")
    items = queries_r.json()["items"]
    if not items:
        pytest.skip("No queries seeded")
    qid = items[0]["query_id"]
    create_r = await client.post("/api/optimizations", json={"query_id": qid})
    opt_id = create_r.json()["optimization_id"]
    r = await client.post(f"/api/optimizations/{opt_id}/reject", json={"reason": "SQL logic incorrect"})
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"
