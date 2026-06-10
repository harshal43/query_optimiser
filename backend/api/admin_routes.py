from fastapi import APIRouter, HTTPException
from ..models.admin_config import AdminConfig
from ..data.admin_store import load_config, save_config

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/config", response_model=AdminConfig)
def get_admin_config():
    return load_config()


@router.post("/config", response_model=AdminConfig)
def post_admin_config(config: AdminConfig):
    try:
        save_config(config)
        return config
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {exc}")
