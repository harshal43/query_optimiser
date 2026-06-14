from __future__ import annotations
import re
from typing import Any


def _scan_ratio(metrics: dict[str, Any]) -> float:
    scanned = metrics.get("bytes_scanned", 0) or 0
    produced = metrics.get("bytes_produced", metrics.get("rows_produced", 1)) or 1
    return scanned / max(produced, 1)


def classify(query_text: str, metrics: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    """Return (classification, severity, issue_type)."""
    text_upper = query_text.upper()
    exec_time_ms = metrics.get("execution_time_ms", 0) or 0
    bytes_spilled = metrics.get("bytes_spilled_remote", 0) or 0
    credits = metrics.get("credits_used", 0) or 0
    join_count = text_upper.count(" JOIN ")
    scan_ratio = _scan_ratio(metrics)

    # 1. Spilling
    if bytes_spilled > 0:
        sev = "critical" if bytes_spilled > 10_000_000 else "high"
        return "spilling", sev, "remote-spill"

    # 2. Scan-heavy
    if scan_ratio > 1000 or credits > 5:
        sev = "critical" if credits > 20 else "high" if credits > 5 else "medium"
        return "scan-heavy", sev, "full-table-scan"

    # 3. Join-inefficient
    if join_count >= 4 or (join_count >= 2 and exec_time_ms > 30_000):
        sev = "high" if join_count >= 6 else "medium"
        return "join-inefficient", sev, "cartesian-or-missing-filter"

    # 4. UDF-bottleneck
    if re.search(r'\b(JAVASCRIPT|PYTHON)\b.*\bFUNCTION\b', text_upper) or \
       re.search(r'\bCALL\s+\w+\s*\(', text_upper):
        return "udf-bottleneck", "medium", "udf-overhead"

    # 5. Repeated-pattern
    if exec_time_ms < 500 and credits > 0.1 and len(query_text) < 300:
        return "repeated-pattern", "low", "high-frequency-small-query"

    # Low-severity slow queries
    if exec_time_ms > 60_000:
        return "scan-heavy", "medium", "slow-execution"

    return None, "low", None
