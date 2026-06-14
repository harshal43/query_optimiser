from __future__ import annotations
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_CONFIG_PATH = "data/admin_config.json"

_DEFAULTS: dict[str, Any] = {
    # LLM Config
    "llm_primary": "claude-sonnet-4",
    "llm_fallback": "gpt-4o",
    "llm_cost_model": "gemini-2.5-flash",
    "llm_timeout_seconds": 30,
    "llm_max_retries": 3,
    # Validation & Safety
    "validation_risk_threshold": 70,
    "auto_approve_enabled": False,
    "circuit_breaker_failures": 5,
    "circuit_breaker_window_seconds": 60,
    "max_variants_per_query": 3,
    "min_confidence_for_approve": "LOW",
    # A/B Testing
    "ab_test_default_traffic_split": 0,
    "ab_test_shadow_duration_hours": 24,
    "ab_test_min_executions": 100,
    "ab_test_p_value_threshold": 0.05,
    "ab_test_auto_promote_enabled": False,
    # Snowflake & Retention
    "snowflake_poll_interval_seconds": 300,
    "snowflake_query_history_days": 30,
    "snowflake_max_queries_per_poll": 500,
    "query_retention_days": 90,
    "optimization_retention_days": 365,
    # Standardization
    "standardization_enabled": True,
    "standardization_enforcement_level": "passive",
    "keyword_uppercase_enabled": True,
    "cte_suggestion_enabled": True,
    "max_query_length_chars": 10000,
    # Webhooks
    "slack_webhook_url": "",
    "email_webhook_url": "",
}

_config: dict[str, Any] = {}


def load_config() -> None:
    global _config
    _config = dict(_DEFAULTS)
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH) as f:
                _config.update(json.load(f))
        except Exception:
            pass


def get_config() -> dict[str, Any]:
    return dict(_config)


def update_config(updates: dict[str, Any]) -> dict[str, Any]:
    allowed = set(_DEFAULTS.keys())
    for k, v in updates.items():
        if k in allowed:
            _config[k] = v
    try:
        os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
        with open(_CONFIG_PATH, "w") as f:
            json.dump(_config, f, indent=2)
    except OSError:
        logger.warning("Failed to persist admin config to %s", _CONFIG_PATH, exc_info=True)
    return dict(_config)
