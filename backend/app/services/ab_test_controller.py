from __future__ import annotations
from typing import Any
from app.db.repositories.ab_tests import create_ab_test, update_ab_test, get_ab_test
from app.services.sse_manager import broadcast


async def start_shadow_test(query_id: str, optimization_id: str) -> str:
    test_id = await create_ab_test(query_id, optimization_id)
    await broadcast("ab_test_created", {
        "test_id": test_id,
        "query_id": query_id,
        "optimization_id": optimization_id,
        "status": "shadow",
        "traffic_split": {"control": 100, "optimized": 0},
    })
    return test_id


async def promote_test(test_id: str, traffic_pct: int = 10) -> dict[str, Any]:
    split = {"control": 100 - traffic_pct, "optimized": traffic_pct}
    await update_ab_test(test_id, status="active", traffic_split=split)
    test = await get_ab_test(test_id)
    await broadcast("ab_test_promoted", {"test_id": test_id, "traffic_split": split})
    return test or {}


async def rollback_test(test_id: str) -> dict[str, Any]:
    await update_ab_test(test_id, status="rolled_back", traffic_split={"control": 100, "optimized": 0})
    test = await get_ab_test(test_id)
    await broadcast("ab_test_rolled_back", {"test_id": test_id})
    return test or {}


async def complete_test(test_id: str, p_value: float) -> dict[str, Any]:
    await update_ab_test(test_id, status="completed", p_value=p_value)
    test = await get_ab_test(test_id)
    await broadcast("ab_test_completed", {"test_id": test_id, "p_value": p_value})
    return test or {}
