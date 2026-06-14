from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query as QParam
from app.db.repositories.queries import list_queries, get_query_by_id
from app.models.query import QueryListResponse, QuerySummary, QueryDetail

router = APIRouter(prefix="/queries", tags=["queries"])


@router.get("", response_model=QueryListResponse)
async def list_queries_endpoint(
    limit: int = QParam(default=50, ge=1, le=200),
    offset: int = QParam(default=0, ge=0),
    severity: str | None = QParam(default=None),
    team: str | None = QParam(default=None),
    status: str | None = QParam(default=None),
):
    items, total = await list_queries(
        limit=limit, offset=offset,
        severity=severity, team_id=team, status=status,
    )
    return QueryListResponse(
        items=[QuerySummary(**i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{query_id}", response_model=QueryDetail)
async def get_query_endpoint(query_id: str):
    row = await get_query_by_id(query_id)
    if not row:
        raise HTTPException(status_code=404, detail="Query not found")
    return QueryDetail(**row)
