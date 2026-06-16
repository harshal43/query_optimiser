from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class ColumnMeta:
    name: str
    data_type: str
    is_nullable: bool
    constraints: list[str]


@dataclass
class TableMeta:
    columns: list[ColumnMeta]
    clustering_key: Optional[str]
    clustering_depth: Optional[float]
    row_count: Optional[int]


@dataclass
class SnowflakeContext:
    available: bool
    tables: dict[str, TableMeta]
    fetch_errors: list[str] = field(default_factory=list)


# ── TTL cache (module-level singleton) ───────────────────────────────────────

_cache: dict[str, tuple[TableMeta, float]] = {}
_TTL_SECONDS: int = 300


# ── SQL parsing ───────────────────────────────────────────────────────────────

def _extract_tables(sql: str) -> list[str]:
    try:
        import sqlglot
        from sqlglot import exp
        tree = sqlglot.parse_one(sql, dialect="snowflake")
        return list({t.name.upper() for t in tree.find_all(exp.Table) if t.name})
    except Exception:
        return []
