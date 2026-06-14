from __future__ import annotations
import pytest
from httpx import AsyncClient


async def test_admin_config_get(client: AsyncClient):
    r = await client.get("/api/admin/config")
    assert r.status_code == 200
    cfg = r.json()["config"]
    assert "llm_primary" in cfg
    assert "validation_risk_threshold" in cfg
    assert len(cfg) == 28


async def test_admin_config_update(client: AsyncClient):
    r = await client.put("/api/admin/config", json={"config": {"llm_timeout_seconds": 45}})
    assert r.status_code == 200
    assert r.json()["config"]["llm_timeout_seconds"] == 45
    assert r.json()["saved"] is True


async def test_admin_config_ignores_unknown_keys(client: AsyncClient):
    r = await client.put("/api/admin/config", json={"config": {"unknown_key": "bad"}})
    assert r.status_code == 200
    assert "unknown_key" not in r.json()["config"]


async def test_ab_tests_list_empty(client: AsyncClient):
    r = await client.get("/api/ab-tests")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "counts" in data
    assert "total" in data


async def test_approve_creates_ab_test(client: AsyncClient):
    queries_r = await client.get("/api/queries?limit=1")
    items = queries_r.json()["items"]
    if not items:
        pytest.skip("No queries seeded")
    qid = items[0]["query_id"]
    opt_r = await client.post("/api/optimizations", json={"query_id": qid})
    assert opt_r.status_code == 200
    opt_id = opt_r.json()["optimization_id"]
    approve_r = await client.post(f"/api/optimizations/{opt_id}/approve", json={"selected_variant": "v1"})
    assert approve_r.status_code == 200
    data = approve_r.json()
    assert "ab_test_id" in data
    assert data["ab_test_id"] is not None
    ab_r = await client.get(f"/api/ab-tests/{data['ab_test_id']}")
    assert ab_r.status_code == 200
    assert ab_r.json()["status"] == "shadow"


async def test_promote_ab_test(client: AsyncClient):
    queries_r = await client.get("/api/queries?limit=1")
    items = queries_r.json()["items"]
    if not items:
        pytest.skip("No queries seeded")
    qid = items[0]["query_id"]
    opt_r = await client.post("/api/optimizations", json={"query_id": qid})
    opt_id = opt_r.json()["optimization_id"]
    approve_r = await client.post(f"/api/optimizations/{opt_id}/approve", json={})
    test_id = approve_r.json()["ab_test_id"]
    promote_r = await client.post(f"/api/ab-tests/{test_id}/promote", json={"traffic_pct": 10})
    assert promote_r.status_code == 200
    assert promote_r.json()["status"] == "active"
    assert promote_r.json()["traffic_split"]["optimized"] == 10


async def test_rollback_ab_test(client: AsyncClient):
    queries_r = await client.get("/api/queries?limit=1")
    items = queries_r.json()["items"]
    if not items:
        pytest.skip("No queries seeded")
    qid = items[0]["query_id"]
    opt_r = await client.post("/api/optimizations", json={"query_id": qid})
    opt_id = opt_r.json()["optimization_id"]
    approve_r = await client.post(f"/api/optimizations/{opt_id}/approve", json={})
    test_id = approve_r.json()["ab_test_id"]
    rollback_r = await client.post(f"/api/ab-tests/{test_id}/rollback")
    assert rollback_r.status_code == 200
    assert rollback_r.json()["status"] == "rolled_back"
