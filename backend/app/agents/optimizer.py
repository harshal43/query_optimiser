from __future__ import annotations
import logging
import re
from typing import Any

from app.agents.base import BaseAgent
from app.agents.llm import llm_call

logger = logging.getLogger(__name__)

TECHNIQUE_CATALOG = {
    "add_partition_filter": {
        "name": "Partition Filter Push-Down",
        "description": "Add date/key partition filters to reduce scan",
        "avg_credit_reduction_pct": 60,
    },
    "replace_select_star": {
        "name": "Column Projection",
        "description": "Replace SELECT * with explicit column list",
        "avg_credit_reduction_pct": 25,
    },
    "cte_subquery_refactor": {
        "name": "CTE Refactor",
        "description": "Replace nested subqueries with Common Table Expressions",
        "avg_credit_reduction_pct": 30,
    },
    "join_order_optimize": {
        "name": "Join Order Optimization",
        "description": "Reorder joins from largest to smallest table",
        "avg_credit_reduction_pct": 20,
    },
    "add_qualify_clause": {
        "name": "QUALIFY Deduplication",
        "description": "Use QUALIFY with ROW_NUMBER() instead of subquery dedup",
        "avg_credit_reduction_pct": 40,
    },
    "warehouse_right_size": {
        "name": "Warehouse Right-Sizing",
        "description": "Reduce warehouse size for low-concurrency workloads",
        "avg_credit_reduction_pct": 50,
    },
}


class OptimizerAgent(BaseAgent):
    name = "optimizer"

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        query_text = state["query_text"]
        diagnosis = state.get("diagnosis", {})
        classification = state.get("classification")
        metrics = state.get("execution_metrics", {})
        certain = diagnosis.get("certain", [])
        probable = diagnosis.get("probable", [])

        variants: list[dict[str, Any]] = []
        applied_techniques: list[str] = []

        certain_types = {f["type"] for f in certain}
        probable_types = {f["type"] for f in probable}

        if "select_star" in probable_types:
            applied_techniques.append("replace_select_star")
        if "nested_subqueries" in probable_types:
            applied_techniques.append("cte_subquery_refactor")
        if "deep_join_chain" in probable_types:
            applied_techniques.append("join_order_optimize")
        if classification == "repeated-pattern":
            applied_techniques.append("add_qualify_clause")
        if "scan_amplification" in certain_types or classification == "scan-heavy":
            applied_techniques.append("add_partition_filter")
        if (metrics.get("credits_used", 0) or 0) > 5:
            applied_techniques.append("warehouse_right_size")

        # Try LLM-generated rewrite first (v1); fall back to rule-based transforms
        llm_sql = await _llm_rewrite(query_text, applied_techniques, diagnosis)
        if llm_sql and llm_sql.strip() and llm_sql.strip().upper() != query_text.strip().upper():
            variants.append({
                "id": "v1",
                "label": "LLM Optimized",
                "sql": llm_sql.strip(),
                "techniques": applied_techniques[:2],
                "technique_details": [TECHNIQUE_CATALOG[t] for t in applied_techniques[:2] if t in TECHNIQUE_CATALOG],
                "rationale": "AI-generated rewrite applying identified optimization techniques",
                "source": "llm",
                "requires_human_edit": False,
            })
        else:
            variant1_sql = _apply_transforms(query_text, applied_techniques[:2])
            if variant1_sql != query_text:
                has_placeholder, hint = _check_placeholder(variant1_sql, applied_techniques[:2])
                variants.append({
                    "id": "v1",
                    "label": "Optimized (Edit Required)" if has_placeholder else "Optimized",
                    "sql": variant1_sql,
                    "techniques": applied_techniques[:2],
                    "technique_details": [TECHNIQUE_CATALOG[t] for t in applied_techniques[:2] if t in TECHNIQUE_CATALOG],
                    "rationale": "Applied column projection and subquery refactoring",
                    "source": "rules",
                    "requires_human_edit": has_placeholder,
                    "edit_hint": hint,
                })

        if len(applied_techniques) > 2:
            variant2_sql = _apply_transforms(query_text, applied_techniques)
            if variant2_sql != query_text:
                has_placeholder, hint = _check_placeholder(variant2_sql, applied_techniques)
                variants.append({
                    "id": "v2",
                    "label": "Aggressive Optimization (Edit Required)" if has_placeholder else "Aggressive Optimization",
                    "sql": variant2_sql,
                    "techniques": applied_techniques,
                    "technique_details": [TECHNIQUE_CATALOG[t] for t in applied_techniques if t in TECHNIQUE_CATALOG],
                    "rationale": "All applicable optimizations applied — validate correctness carefully",
                    "source": "rules",
                    "requires_human_edit": has_placeholder,
                    "edit_hint": hint,
                })

        if not variants:
            variants.append({
                "id": "v1",
                "label": "Annotated Original",
                "sql": f"-- Optimization analysis: no structural changes needed\n-- Consider warehouse right-sizing if credits > 1\n{query_text}",
                "techniques": [],
                "technique_details": [],
                "rationale": "No automated transforms applicable — manual review recommended",
                "source": "rules",
                "requires_human_edit": False,
            })

        recommended = variants[0]["id"] if variants else None
        return {**state, "variants": variants, "recommended_variant": recommended}


def _apply_transforms(sql: str, techniques: list[str]) -> str:
    result = sql
    for technique in techniques:
        if technique == "replace_select_star":
            result = _replace_select_star(result)
        elif technique == "cte_subquery_refactor":
            result = _add_cte_comment(result)
        elif technique == "add_partition_filter":
            result = _add_partition_comment(result)
    return result


_PLACEHOLDER_MARKERS = [
    "/* specify required columns */",
    "-- TODO:",
    "-- Consider refactoring",
]

_PLACEHOLDER_HINTS: dict[str, str] = {
    "replace_select_star": "Replace /* specify required columns */ with the actual column list (e.g. id, name, created_at)",
    "add_partition_filter": "Replace the -- TODO comment with an actual WHERE clause partition filter",
    "cte_subquery_refactor": "Refactor the subqueries into CTEs as suggested by the comment",
}


def _check_placeholder(sql: str, techniques: list[str]) -> tuple[bool, str]:
    for marker in _PLACEHOLDER_MARKERS:
        if marker in sql:
            for t in techniques:
                if t in _PLACEHOLDER_HINTS:
                    return True, _PLACEHOLDER_HINTS[t]
            return True, "Edit the SQL to complete the optimization before approving"
    return False, ""


def _replace_select_star(sql: str) -> str:
    # Catches SELECT * and SELECT alias.* — replaces * with placeholder
    return re.sub(
        r'\bSELECT\s+(\w+\.)?\*\b',
        lambda m: m.group(0).replace('*', '/* specify required columns */'),
        sql,
        flags=re.IGNORECASE,
    )


def _add_cte_comment(sql: str) -> str:
    if 'SELECT' in sql.upper() and sql.upper().count('SELECT') > 1:
        return f"-- Consider refactoring subqueries to CTEs for better readability and optimization\n{sql}"
    return sql


def _add_partition_comment(sql: str) -> str:
    if 'WHERE' not in sql.upper():
        return f"{sql}\n-- TODO: Add partition filter (e.g., WHERE date_col >= DATEADD(day, -30, CURRENT_DATE()))"
    return sql


async def _llm_rewrite(
    query_text: str,
    techniques: list[str],
    diagnosis: dict[str, Any],
) -> str | None:
    if not techniques:
        return None
    technique_names = [
        TECHNIQUE_CATALOG[t]["name"] for t in techniques if t in TECHNIQUE_CATALOG
    ]
    certain = [f["message"] for f in diagnosis.get("certain", [])]
    probable = [f["message"] for f in diagnosis.get("probable", [])]
    issues = "\n".join(f"- {m}" for m in certain + probable) or "General inefficiency detected."
    prompt = f"""You are a Snowflake SQL optimization expert.

ORIGINAL QUERY:
{query_text}

IDENTIFIED ISSUES:
{issues}

TECHNIQUES TO APPLY: {", ".join(technique_names)}

Rewrite the SQL to apply the listed techniques. Rules:
1. Preserve exact query semantics and output columns
2. Use Snowflake SQL syntax
3. Return ONLY the optimized SQL — no markdown, no explanation, no code fences
4. If a technique cannot be applied safely, skip it"""
    return await llm_call(prompt, temperature=0.1)
