# ------------------------------------------------------------
# MODEL PRICING CONFIGURATION
# ------------------------------------------------------------
# All costs are in USD per 1,000 tokens.
# Update these values to reflect current OpenAI pricing without touching any
# business logic — the cost engine in llm/cost.py reads from this dict.
# ------------------------------------------------------------

MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {
        "prompt_cost_per_1k": 0.005,       # $5.00 / 1M input tokens
        "completion_cost_per_1k": 0.015,   # $15.00 / 1M output tokens
    },
    "gpt-4o-mini": {
        "prompt_cost_per_1k": 0.00015,     # $0.15 / 1M input tokens
        "completion_cost_per_1k": 0.0006, # $0.60 / 1M output tokens
    },
}

SUPPORTED_MODELS: list[str] = list(MODEL_PRICING.keys())
