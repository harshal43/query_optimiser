from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any
from app.services.admin_config import get_config, update_config

router = APIRouter(prefix="/admin", tags=["admin"])


class ConfigUpdate(BaseModel):
    config: dict[str, Any]


@router.get("/config")
async def get_admin_config():
    return {"config": get_config()}


@router.put("/config")
async def put_admin_config(body: ConfigUpdate):
    updated = update_config(body.config)
    return {"config": updated, "saved": True}
