from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import sqlglot
from sqlglot import exp


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
        tree = sqlglot.parse_one(sql, dialect="snowflake")
        return list({t.name.upper() for t in tree.find_all(exp.Table) if t.name})
    except Exception:
        return []


def _fetch_table_meta(conn, db: str, schema: str, table: str) -> Optional[TableMeta]:
    import snowflake.connector

    cur = conn.cursor(snowflake.connector.DictCursor)

    # 1. Column types and nullability
    cur.execute(
        "SELECT column_name, data_type, is_nullable "
        "FROM information_schema.columns "
        "WHERE table_name = %s AND table_schema = %s "
        "ORDER BY ordinal_position",
        (table, schema),
    )
    col_rows = cur.fetchall()
    if not col_rows:
        return None

    # 2. Constraints (PK, UNIQUE, FK)
    cur.execute(
        "SELECT kcu.column_name, tc.constraint_type "
        "FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu "
        "  ON tc.constraint_name = kcu.constraint_name "
        "WHERE tc.table_name = %s AND tc.table_schema = %s",
        (table, schema),
    )
    constraint_rows = cur.fetchall()
    constraints_map: dict[str, list[str]] = {}
    for row in constraint_rows:
        col = (row.get("COLUMN_NAME") or row.get("column_name") or "").upper()
        ctype = row.get("CONSTRAINT_TYPE") or row.get("constraint_type") or ""
        if col and ctype:
            constraints_map.setdefault(col, []).append(ctype)

    columns = [
        ColumnMeta(
            name=(row.get("COLUMN_NAME") or row.get("column_name") or "").upper(),
            data_type=row.get("DATA_TYPE") or row.get("data_type") or "",
            is_nullable=(row.get("IS_NULLABLE") or row.get("is_nullable") or "YES") == "YES",
            constraints=constraints_map.get(
                (row.get("COLUMN_NAME") or row.get("column_name") or "").upper(), []
            ),
        )
        for row in col_rows
    ]

    # 3. Clustering key + row count
    cur.execute(
        "SELECT clustering_key, row_count "
        "FROM information_schema.tables "
        "WHERE table_name = %s AND table_schema = %s",
        (table, schema),
    )
    table_row = cur.fetchone()
    clustering_key: Optional[str] = None
    row_count: Optional[int] = None
    if table_row:
        clustering_key = table_row.get("CLUSTERING_KEY") or table_row.get("clustering_key")
        raw_rc = table_row.get("ROW_COUNT") or table_row.get("row_count")
        row_count = int(raw_rc) if raw_rc is not None else None

    # 4. Clustering depth (system function — may raise if no clustering key)
    clustering_depth: Optional[float] = None
    try:
        cur.execute(f"SELECT system$clustering_depth('{db}.{schema}.{table}')")
        depth_row = cur.fetchone()
        if depth_row:
            val = list(depth_row.values())[0]
            if val is not None:
                clustering_depth = float(val)
    except Exception:
        pass

    return TableMeta(
        columns=columns,
        clustering_key=clustering_key,
        clustering_depth=clustering_depth,
        row_count=row_count,
    )
