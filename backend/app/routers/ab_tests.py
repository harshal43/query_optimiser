from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.repositories.ab_tests import list_ab_tests, get_ab_test
from app.services.ab_test_controller import promote_test, rollback_test, complete_test

router = APIRouter(prefix="/ab-tests", tags=["ab-tests"])


class PromoteRequest(BaseModel):
    traffic_pct: int = 10


class CompleteRequest(BaseModel):
    p_value: float


@router.get("")
async def list_tests(status: str | None = None):
    items = await list_ab_tests(status=status)
    counts = {
        "shadow": sum(1 for i in items if i["status"] == "shadow"),
        "active": sum(1 for i in items if i["status"] == "active"),
        "completed": sum(1 for i in items if i["status"] == "completed"),
        "rolled_back": sum(1 for i in items if i["status"] == "rolled_back"),
    }
    return {"items": items, "total": len(items), "counts": counts}


@router.get("/{test_id}")
async def get_test(test_id: str):
    t = await get_ab_test(test_id)
    if not t:
        raise HTTPException(404, "A/B test not found")
    return t


@router.post("/{test_id}/promote")
async def promote(test_id: str, body: PromoteRequest):
    t = await get_ab_test(test_id)
    if not t:
        raise HTTPException(404, "A/B test not found")
    return await promote_test(test_id, body.traffic_pct)


@router.post("/{test_id}/rollback")
async def rollback(test_id: str):
    t = await get_ab_test(test_id)
    if not t:
        raise HTTPException(404, "A/B test not found")
    return await rollback_test(test_id)


@router.post("/{test_id}/complete")
async def complete(test_id: str, body: CompleteRequest):
    t = await get_ab_test(test_id)
    if not t:
        raise HTTPException(404, "A/B test not found")
    return await complete_test(test_id, body.p_value)
