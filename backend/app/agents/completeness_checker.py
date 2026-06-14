"""
Completeness checker — detects semantic gaps in optimized SQL variants
and generates structured missing_fields with LLM-powered suggestions.
"""
from __future__ import annotations
import json
import logging
import re
from typing import Any

from app.agents.llm import llm_call

logger = logging.getLogger(__name__)

# Pattern-based detection: (marker, field metadata)
_PATTERN_FIELDS: list[dict[str, Any]] = [
    {
        "field_id": "select_columns",
        "label": "Column List",
        "location": "SELECT clause",
        "prompt": "Specify the columns needed (comma-separated). Replace SELECT * with only required columns.",
        "placeholder_text": "/* specify required columns */",
        "required": True,
    },
    {
        "field_id": "partition_filter",
        "label": "Partition Filter",
        "location": "WHERE clause",
        "prompt": "Add a partition filter expression (e.g. date range on a timestamp column).",
        "placeholder_text": "-- TODO:",
        "required": True,
    },
    {
        "field_id": "cte_refactor",
        "label": "CTE Refactor",
        "location": "Query structure",
        "prompt": "Refactor the nested subqueries into named CTEs (WITH clause).",
        "placeholder_text": "-- Consider refactoring",
        "required": False,
    },
]


def _pattern_detect(optimized_sql: str) -> list[dict[str, Any]]:
    found = []
    for field in _PATTERN_FIELDS:
        if field["placeholder_text"] in optimized_sql:
            found.append({**field, "suggestion": ""})
    return found


async def _llm_suggest(
    original_sql: str,
    optimized_sql: str,
    fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not fields:
        return fields

    fields_desc = "\n".join(
        f'- {f["field_id"]}: {f["prompt"]} (location: {f["location"]})'
        for f in fields
    )
    prompt = f"""You are a Snowflake SQL expert helping a human reviewer complete an optimization.

ORIGINAL SQL:
{original_sql[:600]}

OPTIMIZED SQL (with placeholders):
{optimized_sql[:600]}

The following fields need human input to complete the optimization:
{fields_desc}

For each field_id, suggest a concrete, specific value the human should enter based on the table names,
column names, and patterns visible in the SQL above.

Return ONLY a JSON object mapping field_id to suggestion string. Example:
{{"select_columns": "order_id, customer_id, total_amount, status, created_at",
  "partition_filter": "created_at >= DATEADD(day, -30, CURRENT_DATE())"}}

If you cannot determine a good suggestion for a field, use an empty string for that key."""

    raw = await llm_call(prompt, temperature=0.1)
    if not raw:
        return fields
    try:
        suggestions: dict[str, str] = json.loads(raw.strip())
        enriched = []
        for f in fields:
            enriched.append({
                **f,
                "suggestion": suggestions.get(f["field_id"], "") or f.get("suggestion", ""),
            })
        return enriched
    except Exception:
        logger.debug("Completeness LLM response not valid JSON: %s", (raw or "")[:200])
        return fields


async def detect_missing_fields(
    original_sql: str,
    optimized_sql: str,
) -> list[dict[str, Any]]:
    """
    Returns list of missing_field dicts for a variant.
    Each dict: field_id, label, location, prompt, suggestion, placeholder_text, required.
    Empty list = no human input needed.
    """
    fields = _pattern_detect(optimized_sql)
    if not fields:
        return []
    return await _llm_suggest(original_sql, optimized_sql, fields)


def reconstruct_sql(
    optimized_sql: str,
    field_values: dict[str, str],
    missing_fields: list[dict[str, Any]],
) -> str:
    """
    Replace placeholder markers in optimized_sql with human-provided field values.
    Handles the partition filter specially — injects WHERE clause if none exists.
    """
    result = optimized_sql
    for field in missing_fields:
        fid = field["field_id"]
        value = field_values.get(fid, "").strip()
        if not value:
            continue
        placeholder = field["placeholder_text"]

        if fid == "select_columns":
            # Replace entire placeholder comment with column list
            result = result.replace(placeholder, value)

        elif fid == "partition_filter":
            # Remove the TODO comment line and inject WHERE/AND clause
            result = re.sub(
                r'\n?-- TODO:.*$',
                '',
                result,
                flags=re.MULTILINE,
            )
            if re.search(r'\bWHERE\b', result, re.IGNORECASE):
                result = re.sub(
                    r'(\bWHERE\b)',
                    f'WHERE {value} AND ',
                    result,
                    count=1,
                    flags=re.IGNORECASE,
                )
            else:
                result = result.rstrip() + f'\nWHERE {value}'

        elif fid == "cte_refactor":
            # Non-required — replace the comment marker with a WITH stub if value given
            result = result.replace(
                placeholder + " subqueries to CTEs for better readability and optimization",
                f"-- CTE refactor applied: {value}",
            )

    return result
