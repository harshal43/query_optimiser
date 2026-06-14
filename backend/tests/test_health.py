from __future__ import annotations
import pytest


@pytest.mark.asyncio
async def test_health_liveness(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_ready_has_required_checks(client):
    resp = await client.get("/api/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "checks" in data
    assert "db" in data["checks"]
    assert "faiss" in data["checks"]
    assert "snowflake" in data["checks"]


@pytest.mark.asyncio
async def test_health_ready_status_ready_when_db_and_faiss_ok(client):
    resp = await client.get("/api/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checks"]["db"] == "ok"
    assert data["checks"]["faiss"] == "ok"
    assert data["status"] == "ready"


@pytest.mark.asyncio
async def test_health_agents_lists_all_six(client):
    resp = await client.get("/api/health/agents")
    assert resp.status_code == 200
    agents = resp.json()["agents"]
    for name in ["analyzer", "optimizer", "cost_estimator",
                 "validator", "pattern_learner", "standardizer"]:
        assert name in agents
