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
    source: str  # "history" | "live" | "error"
    error: Optional[str] = None


@dataclass
class ComparisonResult:
    pre: QueryKPIs
    post: QueryKPIs
    improvement: dict[str, float]  # metric_name -> pct_change (negative = improvement)
    # Additional metadata for frontend (not part of core dataclass)
    pre_query_id: Optional[str] = field(default=None, repr=False)
    post_query_id: Optional[str] = field(default=None, repr=False)
    pre_source: str = field(default="live", repr=False)