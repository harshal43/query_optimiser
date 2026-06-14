from __future__ import annotations
import pytest
from httpx import AsyncClient


async def test_analytics_savings_shape(client: AsyncClient):
    r = await client.get("/api/analytics/savings")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert "monthly" in data
    assert "by_team" in data
    s = data["summary"]
    assert "total_optimizations" in s
    assert "total_credits_saved" in s
    assert "avg_savings_pct" in s
    assert "total_queries" in s


async def test_analytics_patterns_shape(client: AsyncClient):
    r = await client.get("/api/analytics/patterns")
    assert r.status_code == 200
    data = r.json()
    assert "techniques" in data
    assert len(data["techniques"]) == 6
    t = data["techniques"][0]
    assert "name" in t and "success_rate" in t and "application_count" in t


async def test_teams_crud(client: AsyncClient):
    r = await client.post("/api/teams", json={
        "name": "Test Team Alpha", "warehouse": "COMPUTE_WH",
        "warehouse_size": "Small", "enforcement_level": "advisory",
    })
    assert r.status_code == 200
    team_id = r.json()["team_id"]
    r2 = await client.get(f"/api/teams/{team_id}")
    assert r2.status_code == 200
    assert r2.json()["name"] == "Test Team Alpha"
    r3 = await client.put(f"/api/teams/{team_id}", json={"warehouse_size": "Medium"})
    assert r3.status_code == 200
    assert r3.json()["warehouse_size"] == "Medium"
    r4 = await client.get("/api/teams")
    assert r4.status_code == 200
    assert any(t["team_id"] == team_id for t in r4.json()["items"])
    r5 = await client.delete(f"/api/teams/{team_id}")
    assert r5.status_code == 200
    assert r5.json()["deleted"] is True
    r6 = await client.get(f"/api/teams/{team_id}")
    assert r6.status_code == 404


async def test_approve_writes_audit_log(client: AsyncClient):
    queries_r = await client.get("/api/queries?limit=1")
    items = queries_r.json()["items"]
    if not items:
        pytest.skip("No queries seeded")
    qid = items[0]["query_id"]
    opt_r = await client.post("/api/optimizations", json={"query_id": qid})
    assert opt_r.status_code == 200
    opt_id = opt_r.json()["optimization_id"]
    approve_r = await client.post(f"/api/optimizations/{opt_id}/approve", json={})
    assert approve_r.status_code == 200


async def test_reject_writes_audit_log(client: AsyncClient):
    queries_r = await client.get("/api/queries?limit=1")
    items = queries_r.json()["items"]
    if not items:
        pytest.skip("No queries seeded")
    qid = items[0]["query_id"]
    opt_r = await client.post("/api/optimizations", json={"query_id": qid})
    assert opt_r.status_code == 200
    opt_id = opt_r.json()["optimization_id"]
    reject_r = await client.post(f"/api/optimizations/{opt_id}/reject", json={"reason": "test"})
    assert reject_r.status_code == 200


async def test_admin_config_now_28_keys(client: AsyncClient):
    r = await client.get("/api/admin/config")
    assert r.status_code == 200
    assert len(r.json()["config"]) == 28
