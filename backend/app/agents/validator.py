from __future__ import annotations
from typing import Any
import sqlglot
import sqlglot.expressions as exp

from app.agents.base import BaseAgent


class ValidatorAgent(BaseAgent):
    name = "validator"

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        original_sql = state["query_text"]
        variants = state.get("variants", [])

        checks_per_variant: list[dict[str, Any]] = []
        overall_risk = 0

        for variant in variants:
            variant_sql = variant["sql"]
            checks = _run_checks(original_sql, variant_sql)
            risk_score = _compute_risk(checks)
            checks_per_variant.append({
                "variant_id": variant["id"],
                "checks": checks,
                "risk_score": risk_score,
                "passed": sum(1 for c in checks if c["result"] == "pass"),
                "warnings": sum(1 for c in checks if c["result"] == "warn"),
                "failures": sum(1 for c in checks if c["result"] == "fail"),
            })
            overall_risk = max(overall_risk, risk_score)

        validation_results = {
            "variants": checks_per_variant,
            "overall_risk_score": overall_risk,
            "gate_passed": overall_risk < 70,
        }

        return {**state, "validation_results": validation_results, "risk_score": overall_risk}


def _run_checks(original: str, variant: str) -> list[dict[str, Any]]:
    checks = []

    orig_tables = _extract_tables(original)
    var_tables = _extract_tables(variant)
    missing = orig_tables - var_tables
    extra = var_tables - orig_tables
    checks.append({
        "name": "table_preservation",
        "description": "All original tables referenced in optimized query",
        "result": "pass" if not missing else "warn" if len(missing) <= 1 else "fail",
        "detail": f"Missing: {missing}, Extra: {extra}" if (missing or extra) else "All tables preserved",
    })

    orig_select_count = original.upper().count("SELECT")
    var_select_count = variant.upper().count("SELECT")
    checks.append({
        "name": "select_count",
        "description": "SELECT statement count unchanged",
        "result": "pass" if orig_select_count == var_select_count else "warn",
        "detail": f"Original: {orig_select_count}, Variant: {var_select_count}",
    })

    orig_null = original.upper().count("IS NULL") + original.upper().count("IS NOT NULL")
    var_null = variant.upper().count("IS NULL") + variant.upper().count("IS NOT NULL")
    checks.append({
        "name": "null_handling",
        "description": "NULL handling unchanged",
        "result": "pass" if var_null >= orig_null else "warn",
        "detail": f"Original: {orig_null} NULL checks, Variant: {var_null}",
    })

    orig_joins = original.upper().count(" JOIN ")
    var_joins = variant.upper().count(" JOIN ")
    checks.append({
        "name": "join_count",
        "description": "JOIN count not increased",
        "result": "pass" if var_joins <= orig_joins else "warn",
        "detail": f"Original: {orig_joins} JOINs, Variant: {var_joins}",
    })

    orig_has_where = "WHERE" in original.upper()
    var_has_where = "WHERE" in variant.upper()
    if orig_has_where and not var_has_where:
        result, detail = "fail", "WHERE clause removed — potential data expansion risk"
    elif not orig_has_where and var_has_where:
        result, detail = "warn", "WHERE clause added — verify filter correctness"
    else:
        result, detail = "pass", "WHERE clause presence unchanged"
    checks.append({
        "name": "filter_preservation",
        "description": "WHERE clause presence preserved",
        "result": result,
        "detail": detail,
    })

    return checks


def _extract_tables(sql: str) -> set[str]:
    import re
    try:
        parsed = sqlglot.parse_one(sql, read="snowflake", error_level=sqlglot.ErrorLevel.WARN)
        if parsed:
            return {t.name.upper() for t in parsed.find_all(exp.Table)}
    except Exception:
        pass
    return {m.group(1).upper() for m in re.finditer(r'\bFROM\s+(\w+)', sql, re.I)}


def _compute_risk(checks: list[dict[str, Any]]) -> int:
    weights = {"pass": 0, "warn": 15, "fail": 40}
    return min(sum(weights.get(c["result"], 0) for c in checks), 100)
