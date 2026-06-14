from __future__ import annotations
import json
import logging
from typing import Any
import sqlglot
import sqlglot.expressions as exp

from app.agents.base import BaseAgent
from app.agents.llm import llm_call

logger = logging.getLogger(__name__)


class AnalyzerAgent(BaseAgent):
    name = "analyzer"

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        query_text = state["query_text"]
        metrics = state.get("execution_metrics", {})
        classification = state.get("classification")

        certain: list[dict] = []
        probable: list[dict] = []
        speculative: list[dict] = []

        try:
            parsed = sqlglot.parse_one(query_text, read="snowflake", error_level=sqlglot.ErrorLevel.WARN)
            ast_ok = parsed is not None
        except Exception:
            parsed = None
            ast_ok = False

        spilled = metrics.get("bytes_spilled_remote", 0) or 0
        if spilled > 0:
            certain.append({
                "type": "remote_spill",
                "message": f"Query spilled {_fmt_bytes(spilled)} to remote storage — severe performance degradation",
                "metric": "bytes_spilled_remote",
                "value": spilled,
            })

        credits = metrics.get("credits_used", 0) or 0
        if credits > 10:
            certain.append({
                "type": "high_credit_usage",
                "message": f"Query consumed {credits:.2f} credits — optimization critical",
                "metric": "credits_used",
                "value": credits,
            })

        exec_ms = metrics.get("execution_time_ms", 0) or 0
        bytes_scanned = metrics.get("bytes_scanned", 0) or 0
        rows = metrics.get("rows_produced", 1) or 1

        if bytes_scanned > 0 and rows > 0:
            ratio = bytes_scanned / rows
            if ratio > 1_000_000:
                certain.append({
                    "type": "scan_amplification",
                    "message": f"Scanning {_fmt_bytes(int(ratio))} per output row — missing partition filter or full-table scan",
                    "metric": "bytes_per_row",
                    "value": ratio,
                })

        if ast_ok and parsed:
            joins = list(parsed.find_all(exp.Join))
            if len(joins) >= 4:
                probable.append({
                    "type": "deep_join_chain",
                    "message": f"{len(joins)} JOIN operations detected — consider denormalization or CTEs",
                    "join_count": len(joins),
                })

            selects = list(parsed.find_all(exp.Star))
            if selects:
                probable.append({
                    "type": "select_star",
                    "message": "SELECT * fetches all columns — restrict to required columns only",
                })

            subqueries = list(parsed.find_all(exp.Subquery))
            if len(subqueries) > 1:
                probable.append({
                    "type": "nested_subqueries",
                    "message": f"{len(subqueries)} nested subqueries — consider CTEs for readability and optimization",
                    "count": len(subqueries),
                })

        if exec_ms > 30_000:
            speculative.append({
                "type": "result_caching",
                "message": "Long-running query may benefit from result caching if data changes infrequently",
            })
        if classification == "repeated-pattern":
            speculative.append({
                "type": "query_clustering",
                "message": "High-frequency pattern — consider clustering key alignment or materialized view",
            })

        diagnosis = {
            "certain": certain,
            "probable": probable,
            "speculative": speculative,
            "ast_parsed": ast_ok,
            "primary_classification": classification,
        }

        # Optional LLM enrichment — appends to speculative if API configured
        llm_findings = await _llm_enrich(query_text, metrics, certain, probable)
        if llm_findings:
            diagnosis["speculative"] = speculative + llm_findings
            diagnosis["llm_enriched"] = True

        return {**state, "diagnosis": diagnosis}


async def _llm_enrich(
    query_text: str,
    metrics: dict[str, Any],
    certain: list[dict],
    probable: list[dict],
) -> list[dict]:
    known = [f["message"] for f in certain + probable]
    known_str = "\n".join(f"- {m}" for m in known) if known else "None detected by static analysis."
    prompt = f"""You are a Snowflake SQL performance expert. A static analyzer found the following issues:
{known_str}

Query (first 800 chars):
{query_text[:800]}

Execution metrics: {json.dumps({k: v for k, v in metrics.items() if v})}

Provide up to 3 ADDITIONAL optimization insights NOT already listed above.
Return ONLY a JSON array. Each element: {{"type": "snake_case_id", "message": "one actionable sentence"}}.
If no additional insights, return [].
Do not repeat known issues. Do not add markdown or explanation outside the JSON."""
    raw = await llm_call(prompt, temperature=0.2)
    if not raw:
        return []
    try:
        findings = json.loads(raw.strip())
        if isinstance(findings, list):
            return [f for f in findings if isinstance(f, dict) and "type" in f and "message" in f]
    except Exception:
        logger.debug("Analyzer LLM response not valid JSON: %s", raw[:200])
    return []


def _fmt_bytes(b: int) -> str:
    if b < 1024 ** 2:
        return f"{b / 1024:.1f}KB"
    if b < 1024 ** 3:
        return f"{b / 1024 ** 2:.1f}MB"
    return f"{b / 1024 ** 3:.1f}GB"
