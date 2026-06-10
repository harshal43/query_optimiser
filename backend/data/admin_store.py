import json
from pathlib import Path
from ..models.admin_config import AdminConfig

_CONFIG_PATH = Path(__file__).parent.parent / "admin_config.json"


def load_config() -> AdminConfig:
    if not _CONFIG_PATH.exists():
        return AdminConfig()
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return AdminConfig.model_validate(json.load(f))
    except Exception:
        return AdminConfig()


def save_config(config: AdminConfig) -> None:
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2)
