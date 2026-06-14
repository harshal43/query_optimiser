from __future__ import annotations
import importlib
import pytest


def test_settings_loads_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    import app.config as cfg_module
    importlib.reload(cfg_module)
    assert cfg_module.settings.database_url == "postgresql+asyncpg://u:p@localhost/test"


def test_settings_loads_jwt_secret(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    import app.config as cfg_module
    importlib.reload(cfg_module)
    assert cfg_module.settings.jwt_secret == "test-secret"


def test_settings_default_log_level(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    import app.config as cfg_module
    importlib.reload(cfg_module)
    assert cfg_module.settings.log_level == "INFO"


def test_settings_optional_snowflake_defaults_empty(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    import app.config as cfg_module
    importlib.reload(cfg_module)
    assert cfg_module.settings.snowflake_account == ""
    assert cfg_module.settings.anthropic_api_key == ""
