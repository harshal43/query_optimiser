import os
from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------
# SUPPORTED MODELS
# display_name -> internal model id
# ------------------------------------------------------------

MODEL_DISPLAY_NAMES: dict[str, str] = {
    "Claude 4 Sonnet":   "claude-sonnet-4-6",
    "Claude 3.5 Sonnet": "claude-3-5-sonnet-20241022",
    "GPT-4o":            "gpt-4o",
    "GPT-4o mini":       "gpt-4o-mini",
}

SUPPORTED_MODELS: list[str] = list(MODEL_DISPLAY_NAMES.values())

# Per-model env var names for API key and base URL
_MODEL_ENV: dict[str, dict[str, str]] = {
    "claude-sonnet-4-6": {
        "api_key": "CLAUDE_SONNET_4_API_KEY",
        "base_url": "CLAUDE_SONNET_4_BASE_URL",
        "base_url_default": "https://api.anthropic.com/v1",
    },
    "claude-3-5-sonnet-20241022": {
        "api_key": "CLAUDE_SONNET_35_API_KEY",
        "base_url": "CLAUDE_SONNET_35_BASE_URL",
        "base_url_default": "https://api.anthropic.com/v1",
    },
    "gpt-4o": {
        "api_key": "GPT4O_API_KEY",
        "base_url": "GPT4O_BASE_URL",
        "base_url_default": "https://api.openai.com/v1",
    },
    "gpt-4o-mini": {
        "api_key": "GPT4O_MINI_API_KEY",
        "base_url": "GPT4O_MINI_BASE_URL",
        "base_url_default": "https://api.openai.com/v1",
    },
}

# ------------------------------------------------------------
# MODEL PRICING  (USD per 1,000 tokens)
# ------------------------------------------------------------

MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {
        "prompt_cost_per_1k":      0.005,
        "completion_cost_per_1k":  0.015,
    },
    "gpt-4o-mini": {
        "prompt_cost_per_1k":      0.00015,
        "completion_cost_per_1k":  0.0006,
    },
    "claude-sonnet-4-6": {
        "prompt_cost_per_1k":      0.003,
        "completion_cost_per_1k":  0.015,
    },
    "claude-3-5-sonnet-20241022": {
        "prompt_cost_per_1k":      0.003,
        "completion_cost_per_1k":  0.015,
    },
}


def get_llm_credentials(model_id: str) -> dict[str, str]:
    """Return {"api_key": ..., "base_url": ...} for the given model, read from .env."""
    env = _MODEL_ENV.get(model_id)
    if env is None:
        raise ValueError(f"Unknown model '{model_id}'. Supported: {SUPPORTED_MODELS}")

    api_key = os.environ.get(env["api_key"], "")
    if not api_key:
        raise EnvironmentError(
            f"Missing credential for model '{model_id}'. "
            f"Set {env['api_key']} in .env"
        )

    base_url = os.environ.get(env["base_url"], env["base_url_default"])
    return {"api_key": api_key, "base_url": base_url}
