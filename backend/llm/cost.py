"""Token and cost calculation engine.

Reads pricing exclusively from config.MODEL_PRICING — never hardcoded.

Formulas:
    prompt_cost     = (prompt_tokens / 1000) * prompt_cost_per_1k
    completion_cost = (completion_tokens / 1000) * completion_cost_per_1k
    total_cost      = prompt_cost + completion_cost
"""


from ..config import MODEL_PRICING


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> dict:
    """Return a full cost breakdown dict for one LLM call.

    Raises:
        ValueError — if `model` is not present in MODEL_PRICING.
    """
    if model not in MODEL_PRICING:
        raise ValueError(
            f"Unknown model '{model}'. Supported models: {list(MODEL_PRICING.keys())}"
        )

    pricing = MODEL_PRICING[model]

    prompt_cost = (prompt_tokens / 1000) * pricing["prompt_cost_per_1k"]
    completion_cost = (completion_tokens / 1000) * pricing["completion_cost_per_1k"]
    total_cost = prompt_cost + completion_cost
    total_tokens = prompt_tokens + completion_tokens

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "prompt_cost": round(prompt_cost, 8),
        "completion_cost": round(completion_cost, 8),
        "total_cost": round(total_cost, 8),
    }
