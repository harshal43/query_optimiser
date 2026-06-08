from pydantic import BaseModel
from typing import Optional


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
    percentage_comparison: float


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


# ------------------------------------------------------------
# Snowflake connector schemas
# ------------------------------------------------------------

class SnowflakeCredentials(BaseModel):
    account: str
    user: str
    password: str
    role: str = ""
    warehouse: str = ""
    database: str = ""
    schema_name: str = ""


class SnowflakeConnectResponse(BaseModel):
    connected: bool
    account: Optional[str] = None
    message: str


class SnowflakeStatusResponse(BaseModel):
    connected: bool
    account: Optional[str] = None
    message: str


class SnowflakeQueryRow(BaseModel):
    query_id: str
    query_text: str
    credits: float
    frequency: Optional[int] = None
    score: Optional[float] = None
