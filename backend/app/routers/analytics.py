from __future__ import annotations
from fastapi import APIRouter
from app.db.repositories.analytics import (
    savings_summary, savings_by_month, savings_by_team, technique_effectiveness,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/savings")
async def get_savings():
    summary = await savings_summary()
    monthly = await savings_by_month()
    by_team = await savings_by_team()
    return {"summary": summary, "monthly": monthly, "by_team": by_team}


@router.get("/patterns")
async def get_patterns():
    techniques = await technique_effectiveness()
    return {"techniques": techniques, "total": len(techniques)}
