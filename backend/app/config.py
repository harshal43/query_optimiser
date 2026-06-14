from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    jwt_secret: str
    log_level: str = "INFO"
    app_env: str = "development"

    snowflake_account: str = ""
    snowflake_user: str = ""
    snowflake_private_key_path: str = ""
    snowflake_role: str = "ACCOUNTADMIN"
    snowflake_warehouse: str = "COMPUTE_WH"
    snowflake_database: str = "SNOWFLAKE"
    snowflake_schema: str = "ACCOUNT_USAGE"

    # Same endpoint for all models — per-model API keys
    api_url: str = ""
    anthropic_api_key: str = ""   # claude-* models
    openai_api_key: str = ""      # gpt-* models
    google_api_key: str = ""      # gemini-* models


settings = Settings()
