from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QueryKPIs:
    query_id: str
    elapsed_ms: Optional[int]
    bytes_scanned: Optional[int]
    bytes_spilled_local: Optional[int]
    bytes_spilled_remote: Optional[int]
    partitions_scanned: Optional[int]
    partitions_total: Optional[int]
    rows_produced: Optional[int]
    credits: Optional[float]
    source: str  # "history" | "live"
    error: Optional[str] = None


@dataclass
class ComparisonResult:
    pre: QueryKPIs
    post: QueryKPIs
    improvement: dict  # metric_name → pct_change (negative = improvement)
