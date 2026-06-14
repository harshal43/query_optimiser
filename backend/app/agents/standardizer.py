from __future__ import annotations
import re
from typing import Any

from app.agents.base import BaseAgent

_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER",
    "ON", "AND", "OR", "NOT", "IN", "AS", "GROUP BY", "ORDER BY", "HAVING",
    "LIMIT", "OFFSET", "UNION", "ALL", "DISTINCT", "WITH", "CASE", "WHEN",
    "THEN", "ELSE", "END", "NULL", "IS", "BETWEEN", "LIKE", "EXISTS",
]


class StandardizerAgent(BaseAgent):
    name = "standardizer"

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        variants = state.get("variants", [])
        standardized = []
        for v in variants:
            sql = v["sql"]
            sql = _uppercase_keywords(sql)
            sql = _normalize_whitespace(sql)
            standardized.append({**v, "sql": sql})
        return {**state, "variants": standardized}


def _uppercase_keywords(sql: str) -> str:
    for kw in _KEYWORDS:
        sql = re.sub(rf'\b{kw}\b', kw, sql, flags=re.IGNORECASE)
    return sql


def _normalize_whitespace(sql: str) -> str:
    sql = re.sub(r'\n{3,}', '\n\n', sql)
    sql = re.sub(r'[ \t]+', ' ', sql)
    return sql.strip()
