from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from app.db.repositories.teams import list_teams, get_team, insert_team, update_team, delete_team

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamCreate(BaseModel):
    name: str
    warehouse: str = "COMPUTE_WH"
    warehouse_size: str = "X-Small"
    enforcement_level: str = "passive"
    ab_test_config: dict[str, Any] = {}
    standardization_rules: dict[str, Any] = {}


class TeamUpdate(BaseModel):
    name: str | None = None
    warehouse: str | None = None
    warehouse_size: str | None = None
    enforcement_level: str | None = None
    ab_test_config: dict[str, Any] | None = None


@router.get("")
async def list_teams_endpoint():
    items = await list_teams()
    return {"items": items, "total": len(items)}


@router.post("")
async def create_team(body: TeamCreate):
    team_id = await insert_team(
        name=body.name,
        warehouse=body.warehouse,
        warehouse_size=body.warehouse_size,
        enforcement_level=body.enforcement_level,
        ab_test_config=body.ab_test_config,
        standardization_rules=body.standardization_rules,
    )
    return {"team_id": team_id, "name": body.name}


@router.get("/{team_id}")
async def get_team_endpoint(team_id: str):
    team = await get_team(team_id)
    if not team:
        raise HTTPException(404, "Team not found")
    return team


@router.put("/{team_id}")
async def update_team_endpoint(team_id: str, body: TeamUpdate):
    team = await get_team(team_id)
    if not team:
        raise HTTPException(404, "Team not found")
    await update_team(
        team_id=team_id,
        name=body.name,
        warehouse=body.warehouse,
        warehouse_size=body.warehouse_size,
        enforcement_level=body.enforcement_level,
        ab_test_config=body.ab_test_config,
    )
    return await get_team(team_id)


@router.delete("/{team_id}")
async def delete_team_endpoint(team_id: str):
    deleted = await delete_team(team_id)
    if not deleted:
        raise HTTPException(404, "Team not found")
    return {"deleted": True}
