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
    edited_sql: str | None = None  # human-provided SQL when variant.requires_human_edit is True


class RejectRequest(BaseModel):
    reason: str
