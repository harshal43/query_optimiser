from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException
from app.db.repositories.queries import get_query_by_id
from app.db.repositories.optimizations import (
    insert_optimization, get_optimization_by_id, list_optimizations,
    update_optimization_status, update_query_status,
)
from app.agents.graph import run_optimization_pipeline
from app.models.optimization import OptimizationResponse, OptimizeRequest, ApproveRequest, RejectRequest

router = APIRouter(prefix="/optimizations", tags=["optimizations"])
logger = logging.getLogger(__name__)


@router.post("")
async def create_optimization(body: OptimizeRequest):
    query = await get_query_by_id(body.query_id)
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    try:
        result = await run_optimization_pipeline(
            query_id=query["query_id"],
            query_text=query["query_text"],
            query_hash=query["query_hash"],
            classification=query.get("classification"),
            severity=query.get("severity"),
            execution_metrics=query.get("execution_metrics", {}),
        )
    except Exception as e:
        logger.error("Pipeline failed for query %s: %s", body.query_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")
    optimization_id = await insert_optimization(
        query_id=query["query_id"],
        diagnosis=result.get("diagnosis", {}),
        variants=result.get("variants", []),
        cost_predictions=result.get("cost_predictions", {}),
        validation_results=result.get("validation_results", {}),
        recommended_variant=result.get("recommended_variant"),
    )
    return {"optimization_id": optimization_id, "query_id": query["query_id"], "status": "pending_review"}


@router.get("")
async def list_optimizations_endpoint(status: str | None = None, query_id: str | None = None):
    items = await list_optimizations(status=status, query_id=query_id)
    return {"items": items, "total": len(items)}


@router.get("/{optimization_id}", response_model=OptimizationResponse)
async def get_optimization(optimization_id: str):
    row = await get_optimization_by_id(optimization_id)
    if not row:
        raise HTTPException(status_code=404, detail="Optimization not found")
    return OptimizationResponse(**row)


@router.post("/{optimization_id}/approve")
async def approve_optimization(optimization_id: str, body: ApproveRequest):
    row = await get_optimization_by_id(optimization_id)
    if not row:
        raise HTTPException(status_code=404, detail="Optimization not found")
    await update_optimization_status(optimization_id, "approved", body.selected_variant)
    await update_query_status(row["query_id"], "approved")
    from app.db.repositories.audit_log import insert_audit_log
    from app.services.ab_test_controller import start_shadow_test
    from app.services.sse_manager import broadcast
    from app.services.webhooks import fire_webhook
    await insert_audit_log(
        actor="user",
        action="optimization_approved",
        resource_type="optimization",
        resource_id=optimization_id,
        payload={"query_id": row["query_id"], "selected_variant": body.selected_variant},
    )
    test_id: str | None = None
    try:
        test_id = await start_shadow_test(row["query_id"], optimization_id)
        await broadcast("review_required", {
            "event": "optimization_approved",
            "optimization_id": optimization_id,
            "query_id": row["query_id"],
            "ab_test_id": test_id,
        })
        await fire_webhook("optimization_approved", {"optimization_id": optimization_id, "ab_test_id": test_id})
    except Exception:
        logger.error("Failed to create A/B test for optimization %s", optimization_id, exc_info=True)
    return {"optimization_id": optimization_id, "status": "approved", "ab_test_id": test_id}


@router.post("/{optimization_id}/reject")
async def reject_optimization(optimization_id: str, body: RejectRequest):
    row = await get_optimization_by_id(optimization_id)
    if not row:
        raise HTTPException(status_code=404, detail="Optimization not found")
    await update_optimization_status(optimization_id, "rejected")
    await update_query_status(row["query_id"], "rejected")
    from app.db.repositories.audit_log import insert_audit_log
    await insert_audit_log(
        actor="user",
        action="optimization_rejected",
        resource_type="optimization",
        resource_id=optimization_id,
        payload={"query_id": row["query_id"], "reason": body.reason},
    )
    logger.info("Optimization %s rejected: %s", optimization_id, body.reason)
    return {"optimization_id": optimization_id, "status": "rejected", "reason": body.reason}
