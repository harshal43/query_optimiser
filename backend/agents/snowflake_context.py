from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)


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
_cache_connection_key: str = ""  # tracks "db.schema" for the last connection
_TTL_SECONDS: int = 300
_IDENT_RE = re.compile(r'^[A-Za-z0-9_$]+$')


# ── SQL parsing ───────────────────────────────────────────────────────────────

def _extract_tables(sql: str) -> list[str]:
    try:
        tree = sqlglot.parse_one(sql, dialect="snowflake")
        return list({t.name.upper() for t in tree.find_all(exp.Table) if t.name})
    except Exception:
        return []


def _fetch_table_meta(conn, db: str, schema: str, table: str) -> Optional[TableMeta]:
    # Need a known db to qualify information_schema; unqualified refs fail with 090105
    if not db:
        return None
    if not (_IDENT_RE.match(db) and _IDENT_RE.match(schema) and _IDENT_RE.match(table)):
        return None

    import snowflake.connector

    cur = conn.cursor(snowflake.connector.DictCursor)
    info = f"{db}.information_schema"

    # 1. Column types and nullability
    cur.execute(
        f"SELECT column_name, data_type, is_nullable "
        f"FROM {info}.columns "
        "WHERE table_name = %s AND table_schema = %s "
        "ORDER BY ordinal_position",
        (table, schema),
    )
    col_rows = cur.fetchall()
    if not col_rows:
        return None

    # 2. Constraints (PK, UNIQUE, FK)
    cur.execute(
        f"SELECT kcu.column_name, tc.constraint_type "
        f"FROM {info}.table_constraints tc "
        f"JOIN {info}.key_column_usage kcu "
        "  ON tc.constraint_name = kcu.constraint_name "
        "  AND kcu.table_name = tc.table_name "
        "  AND kcu.table_schema = tc.table_schema "
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

    columns = []
    for row in col_rows:
        col_name = (row.get("COLUMN_NAME") or row.get("column_name") or "").upper()
        columns.append(ColumnMeta(
            name=col_name,
            data_type=row.get("DATA_TYPE") or row.get("data_type") or "",
            is_nullable=(row.get("IS_NULLABLE") or row.get("is_nullable") or "YES") == "YES",
            constraints=constraints_map.get(col_name, []),
        ))

    # 3. Clustering key + row count
    cur.execute(
        f"SELECT clustering_key, row_count "
        f"FROM {info}.tables "
        "WHERE table_name = %s AND table_schema = %s",
        (table, schema),
    )
    table_row = cur.fetchone()
    clustering_key: Optional[str] = None
    row_count: Optional[int] = None
    if table_row:
        clustering_key = table_row.get("CLUSTERING_KEY") or table_row.get("clustering_key")
        raw_rc = table_row.get("ROW_COUNT")
        if raw_rc is None:
            raw_rc = table_row.get("row_count")
        row_count = int(raw_rc) if raw_rc is not None else None

    # 4. Clustering depth — only if clustering_key and db is known
    clustering_depth: Optional[float] = None
    if clustering_key and db:
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


def fetch_snowflake_context(sql: str) -> SnowflakeContext:
    """
    Parse sql, fetch schema + clustering metadata for all referenced tables.
    Returns SnowflakeContext(available=False) if Snowflake is not connected.
    Never raises — all errors are logged to fetch_errors.
    """
    from ..data import snowflake_connector as sc

    if not sc.is_connected():
        logger.debug("── Agent3/SnowflakeContext | Snowflake not connected — skipping metadata fetch")
        return SnowflakeContext(available=False, tables={})

    tables = _extract_tables(sql)
    logger.info("── Agent3/SnowflakeContext START | tables_found=%s", tables)
    if not tables:
        return SnowflakeContext(available=True, tables={})

    creds = sc._creds or {}
    db = (creds.get("database") or "").upper()
    schema = (creds.get("schema_name") or "PUBLIC").upper()
    conn = sc._conn

    # Fix 1 — TOCTOU: conn could become None after is_connected() returned True
    if conn is None:
        logger.warning("── Agent3/SnowflakeContext | conn became None after is_connected() — degrading gracefully")
        return SnowflakeContext(available=False, tables={})

    # Fix 3 — clear cache when db/schema changes (e.g. reconnect to different database)
    global _cache_connection_key
    connection_key = f"{db}.{schema}"
    if connection_key != _cache_connection_key:
        logger.debug("── Agent3/SnowflakeContext | connection_key changed (%r → %r) — cache cleared", _cache_connection_key, connection_key)
        _cache.clear()
        _cache_connection_key = connection_key

    result: dict[str, TableMeta] = {}
    errors: list[str] = []
    now = time.monotonic()

    for table in tables:
        # Fix 2 — include db in cache key to avoid cross-database collisions
        cache_key = f"{db}.{schema}.{table}"
        if cache_key in _cache:
            meta, fetched_at = _cache[cache_key]
            if now - fetched_at < _TTL_SECONDS:
                logger.debug("── Agent3/SnowflakeContext | cache_hit | table=%s | age=%.1fs", cache_key, now - fetched_at)
                result[table] = meta
                continue

        try:
            meta = _fetch_table_meta(conn, db, schema, table)
            if meta is None:
                # Fix 6 — message is accurate for both "table absent" and "name rejected"
                errors.append(f"Could not fetch metadata for table: {table}")
                logger.warning("── Agent3/SnowflakeContext | table_not_found | table=%s", table)
                continue
            logger.debug(
                "── Agent3/SnowflakeContext | fetched | table=%s | cols=%d | clustering_key=%r | row_count=%s",
                table, len(meta.columns), meta.clustering_key, meta.row_count,
            )
            # Fix 5 — fresh timestamp so TTL isn't shortened by loop latency
            _cache[cache_key] = (meta, time.monotonic())
            result[table] = meta
        except Exception as exc:
            errors.append(f"Error fetching {table}: {exc}")
            logger.exception("── Agent3/SnowflakeContext | fetch_error | table=%s | error=%s", table, exc)

    logger.info(
        "── Agent3/SnowflakeContext DONE | fetched=%s | errors=%s",
        list(result.keys()), errors or "none",
    )
    return SnowflakeContext(available=True, tables=result, fetch_errors=errors)


def build_context_block(sf_context: SnowflakeContext, strict: bool = False) -> str:
    """
    Render SnowflakeContext as a text block for injection into agent system prompts.
    strict=True emits a hard constraint header for the optimizer; False emits informational header for advisor.
    Returns empty string when not available or no tables fetched.
    """
    if not sf_context.available or not sf_context.tables:
        return ""

    if strict:
        header = (
            "\n\nSTRICT SCHEMA CONSTRAINT — THIS IS AUTHORITATIVE:\n"
            "The schema below is the ONLY valid reference for column and table names. Rules:\n"
            "1. ONLY use column names that appear in this schema.\n"
            "2. NEVER invent, guess, or introduce columns not listed here.\n"
            "3. If a suggestion requires a column absent from this schema, skip that suggestion.\n"
            "4. Preserve all original column names exactly as they appear.\n"
            "\nVerified Snowflake Schema (authoritative — do not deviate):"
        )
    else:
        header = "\n\nSnowflake Metadata (fetched live — use this to validate your suggestions):"

    lines = [header]
    for table_name, meta in sf_context.tables.items():
        lines.append(f"\nTable: {table_name}")
        if meta.columns:
            col_parts = []
            for col in meta.columns:
                nullable = "NOT NULL" if not col.is_nullable else "nullable"
                tags = [col.data_type, nullable] + col.constraints
                col_parts.append(f"{col.name} ({', '.join(tags)})")
            lines.append(f"  Columns: {', '.join(col_parts)}")
        lines.append(f"  Clustering Key: {meta.clustering_key or 'none'}")
        if meta.clustering_depth is not None:
            note = (
                "← poor clustering, many micro-partitions to scan"
                if meta.clustering_depth > 0.7
                else "← well clustered"
            )
            lines.append(f"  Clustering Depth: {meta.clustering_depth:.2f}  {note}")
        if meta.row_count is not None:
            lines.append(f"  Row Count: {meta.row_count:,}")
    return "\n".join(lines)


def validate_query_schema(sql: str, sf_context: SnowflakeContext) -> list[str]:
    """
    Parse sql and return column names that don't exist in sf_context schema.
    Only validates when schema is available; returns [] otherwise (can't validate = no warning).
    CTE names and column aliases defined within the query are excluded from violations.
    """
    if not sf_context or not sf_context.available or not sf_context.tables:
        return []

    try:
        tree = sqlglot.parse_one(sql, dialect="snowflake")
    except Exception:
        return []

    # All known columns across all fetched tables
    known: set[str] = set()
    for meta in sf_context.tables.values():
        for col in meta.columns:
            known.add(col.name.upper())

    # Aliases and CTE names defined within the query — not hallucinations
    defined_in_query: set[str] = set()
    for node in tree.find_all(exp.Alias):
        if node.alias:
            defined_in_query.add(node.alias.upper())
    for node in tree.find_all(exp.CTE):
        if node.alias:
            defined_in_query.add(node.alias.upper())

    seen: set[str] = set()
    violations: list[str] = []
    for node in tree.find_all(exp.Column):
        name = node.name.upper()
        if not name or name in seen:
            continue
        seen.add(name)
        if name not in known and name not in defined_in_query:
            violations.append(name)

    return violations


def find_recent_query_run(conn, sql_text: str) -> Optional[str]:
    """
    Search INFORMATION_SCHEMA.QUERY_HISTORY for a recent successful run of sql_text.
    Returns the QUERY_ID string, or None if not found.
    Uses the first 100 chars of normalised SQL as the LIKE search fragment.
    """
    from ..data import snowflake_connector as sc
    import snowflake.connector

    fingerprint = " ".join(sql_text.split())[:500]
    search_fragment = fingerprint[:100].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    creds = sc._creds or {}
    db = (creds.get("database") or "").strip().upper()

    cur = conn.cursor(snowflake.connector.DictCursor)
    # INFORMATION_SCHEMA.QUERY_HISTORY requires a database context (error 090105 otherwise)
    if db and _IDENT_RE.match(db):
        cur.execute(f"USE DATABASE {db}")
    cur.execute(
        """
        SELECT QUERY_ID
        FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY(
            RESULT_LIMIT => 200,
            END_TIME_RANGE_START => DATEADD('days', -7, CURRENT_TIMESTAMP())
        ))
        WHERE UPPER(QUERY_TEXT) LIKE UPPER(%s)
          AND EXECUTION_STATUS = 'SUCCESS'
          AND QUERY_TYPE = 'SELECT'
        ORDER BY START_TIME DESC
        LIMIT 1
        """,
        (f"%{search_fragment}%",),
    )
    row = cur.fetchone()
    if row:
        return row.get("QUERY_ID") or row.get("query_id")
    return None


def fetch_query_kpis(conn, query_id: str, source: str = "history") -> "QueryKPIs":
    """
    Fetch execution metrics for a specific query_id from INFORMATION_SCHEMA.QUERY_HISTORY.
    Returns a QueryKPIs with error set if the query_id is not found.
    """
    from ..models.kpi_models import QueryKPIs
    from ..data import snowflake_connector as sc
    import snowflake.connector

    creds = sc._creds or {}
    db = (creds.get("database") or "").strip().upper()

    cur = conn.cursor(snowflake.connector.DictCursor)
    if db and _IDENT_RE.match(db):
        cur.execute(f"USE DATABASE {db}")
    cur.execute(
        """
        SELECT
            QUERY_ID,
            TOTAL_ELAPSED_TIME,
            BYTES_SCANNED,
            BYTES_SPILLED_TO_LOCAL_STORAGE,
            BYTES_SPILLED_TO_REMOTE_STORAGE,
            PARTITIONS_SCANNED,
            PARTITIONS_TOTAL,
            ROWS_PRODUCED,
            CREDITS_USED_CLOUD_SERVICES
        FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY(RESULT_LIMIT => 200))
        WHERE QUERY_ID = %s
        """,
        (query_id,),
    )
    row = cur.fetchone()
    if row is None:
        return QueryKPIs(
            query_id=query_id,
            elapsed_ms=None, bytes_scanned=None,
            bytes_spilled_local=None, bytes_spilled_remote=None,
            partitions_scanned=None, partitions_total=None,
            rows_produced=None, credits=None,
            source=source,
            error=f"Query ID {query_id!r} not found in INFORMATION_SCHEMA.QUERY_HISTORY",
        )

    def _int(key: str) -> Optional[int]:
        v = row.get(key)
        return int(v) if v is not None else None

    def _float(key: str) -> Optional[float]:
        v = row.get(key)
        return float(v) if v is not None else None

    return QueryKPIs(
        query_id=query_id,
        elapsed_ms=_int("TOTAL_ELAPSED_TIME"),
        bytes_scanned=_int("BYTES_SCANNED"),
        bytes_spilled_local=_int("BYTES_SPILLED_TO_LOCAL_STORAGE"),
        bytes_spilled_remote=_int("BYTES_SPILLED_TO_REMOTE_STORAGE"),
        partitions_scanned=_int("PARTITIONS_SCANNED"),
        partitions_total=_int("PARTITIONS_TOTAL"),
        rows_produced=_int("ROWS_PRODUCED"),
        credits=_float("CREDITS_USED_CLOUD_SERVICES"),
        source=source,
        error=None,
    )
