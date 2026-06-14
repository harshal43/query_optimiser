from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel
from typing_extensions import TypedDict


class OptimizationState(TypedDict):
    query_id: str
    query_text: str
    query_hash: str
    classification: str | None
    severity: str | None
    execution_metrics: dict[str, Any]
    diagnosis: dict[str, Any]
    variants: list[dict[str, Any]]
    cost_predictions: dict[str, Any]
    validation_results: dict[str, Any]
    risk_score: int
    recommended_variant: str | None
    error: str | None


class OptimizationResponse(BaseModel):
    optimization_id: str
    query_id: str
    diagnosis: dict[str, Any]
    variants: list[dict[str, Any]]
    cost_predictions: dict[str, Any]
    validation_results: dict[str, Any]
    recommended_variant: str | None
    user_selected_variant: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class OptimizeRequest(BaseModel):
    query_id: str


class ApproveRequest(BaseModel):
    selected_variant: str | None = None
    edited_sql: str | None = None          # raw SQL override (fallback)
    field_values: dict[str, str] | None = None  # structured: {field_id: human_value}


class RejectRequest(BaseModel):
    reason: str
