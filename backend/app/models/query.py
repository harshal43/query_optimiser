from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class QuerySummary(BaseModel):
    query_id: str
    query_preview: str | None
    team_id: str | None
    warehouse: str | None
    warehouse_size: str | None
    severity: str | None
    issue_type: str | None
    status: str
    ingestion_timestamp: datetime
    execution_metrics: dict[str, Any]


class QueryDetail(BaseModel):
    query_id: str
    query_text: str
    query_hash: str
    query_preview: str | None
    team_id: str | None
    warehouse: str | None
    warehouse_size: str | None
    classification: str | None
    severity: str | None
    issue_type: str | None
    execution_metrics: dict[str, Any]
    ingestion_timestamp: datetime
    source: str
    status: str


class QueryListResponse(BaseModel):
    items: list[QuerySummary]
    total: int
    limit: int
    offset: int
