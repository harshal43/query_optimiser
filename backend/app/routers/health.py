from __future__ import annotations
import logging
from fastapi import APIRouter
from app.db.connection import get_pool
from app.vector.index import get_index, INDEX_NAMES

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_liveness():
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready():
    checks: dict[str, str] = {}

    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        checks["db"] = "ok"
    except Exception as exc:
        logger.error("DB health check failed", exc_info=True)
        checks["db"] = f"error: {exc}"

    try:
        for name in INDEX_NAMES:
            get_index(name)
        checks["faiss"] = "ok"
    except Exception as exc:
        logger.error("FAISS health check failed", exc_info=True)
        checks["faiss"] = f"error: {exc}"

    checks["snowflake"] = "not_configured"

    all_ok = all(v == "ok" for k, v in checks.items() if k != "snowflake")
    return {"status": "ready" if all_ok else "degraded", "checks": checks}


@router.get("/health/agents")
async def health_agents():
    try:
        from app.agents.graph import agent_health
        return {"agents": agent_health()}
    except Exception:
        agent_names = ["analyzer", "optimizer", "cost_estimator", "validator", "pattern_learner", "standardizer"]
        return {"agents": {name: "not_initialized" for name in agent_names}}
