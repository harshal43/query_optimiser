from pydantic import BaseModel, Field
from typing import Optional


# ------------------------------------------------------------
# Request models
# ------------------------------------------------------------

class LLMConfig(BaseModel):
    api_key: str = Field(..., description="OpenAI-compatible API key")
    base_url: str = Field(..., description="Full endpoint URL or base URL")
    model: str = Field(..., description="Model identifier, e.g. gpt-4o")
    endpoint_type: Optional[str] = Field(
        "standard", description="'standard' (OpenAI) or 'trustai' (routed OpenAI-compatible)"
    )


class OptimizationRequest(BaseModel):
    query_id: str
    llm_config: LLMConfig
    selected_suggestions: list[str]  # full_text of each user-selected suggestion


class AnalyzeCustomRequest(BaseModel):
    query_text: str
    credits: float = 0.0
    llm_config: LLMConfig


class OptimizeCustomRequest(BaseModel):
    query_text: str
    credits: float = 0.0
    llm_config: LLMConfig
    selected_suggestions: list[str]


# ------------------------------------------------------------
# Response models
# ------------------------------------------------------------

class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_cost: float
    completion_cost: float
    total_cost: float


class AdvisorResult(BaseModel):
    suggestions: str
    token_usage: TokenUsage


class OptimizerResult(BaseModel):
    optimized_query: str
    explanation: str
    raw_response: str
    token_usage: TokenUsage


class CostComparison(BaseModel):
    snowflake_credits: float
    total_llm_cost: float
    absolute_difference: float
    percentage_comparison: float  # (LLM cost / credits) * 100


class OptimizationResponse(BaseModel):
    query_id: str
    original_query: str
    advisor_result: AdvisorResult
    optimizer_result: OptimizerResult
    total_llm_cost: float
    cost_comparison: CostComparison


class QueryDetail(BaseModel):
    query_id: str
    query_text: str
    credits: float


class QueryListResponse(BaseModel):
    query_ids: list[str]
