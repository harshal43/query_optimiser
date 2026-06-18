"""Agent 3 - Snowflake Context Fetcher

Fetches live schema metadata (columns, constraints, clustering, row counts)
for all tables referenced in a SQL query.
"""

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
    # NEW: Track which tables were requested vs found
    requested_tables: list[str] = field(default_factory=list)
    # NEW: Current database/schema context used for fetching
    resolved_db: Optional[str] = None
    resolved_schema: Optional[str] = None


# ── TTL cache (module-level singleton) ───────────────────────────────────────

_cache: dict[str, tuple[TableMeta, float]] = {}
_cache_connection_key: str = ""  # tracks "db.schema" for the last connection
_TTL_SECONDS: int = 300
_IDENT_RE = re.compile(r'^[A-Za-z0-9_$]+$')


# ── SQL parsing ───────────────────────────────────────────────────────────────

def _extract_tables(sql: str) -> list[str]:
    """Extract table names from SQL, handling fully-qualified names."""
    try:
        tree = sqlglot.parse_one(sql, dialect="snowflake")
        tables = []
        for t in tree.find_all(exp.Table):
            if t.name:
                # Store the table name; if fully qualified, we'll parse db.schema.table
                tables.append(t.name.upper())
        return list(dict.fromkeys(tables))  # preserve order, remove duplicates
    except Exception as exc:
        logger.warning("Failed to parse SQL for table extraction: %s", exc)
        return []


def _extract_fully_qualified_tables(sql: str) -> list[dict]:
    """Extract tables with their db.schema qualifiers if present."""
    try:
        tree = sqlglot.parse_one(sql, dialect="snowflake")
        result = []
        for t in tree.find_all(exp.Table):
            if t.name:
                result.append({
                    "table": t.name.upper(),
                    "db": (t.args.get("db") or "").upper() if hasattr(t, "args") else "",
                    "schema": (t.args.get("schema") or "").upper() if hasattr(t, "args") else "",
                })
        return result
    except Exception:
        return []


# ── Database/Schema Resolution ────────────────────────────────────────────────

def _get_current_database(conn) -> Optional[str]:
    """Get the current database from the session."""
    import snowflake.connector
    try:
        cur = conn.cursor(snowflake.connector.DictCursor)
        cur.execute("SELECT CURRENT_DATABASE() AS DB")
        row = cur.fetchone()
        if row:
            return (row.get("DB") or row.get("db") or "").strip().upper() or None
    except Exception as exc:
        logger.warning("Failed to get current database: %s", exc)
    return None


def _get_current_schema(conn) -> Optional[str]:
    """Get the current schema from the session."""
    import snowflake.connector
    try:
        cur = conn.cursor(snowflake.connector.DictCursor)
        cur.execute("SELECT CURRENT_SCHEMA() AS SCH")
        row = cur.fetchone()
        if row:
            return (row.get("SCH") or row.get("sch") or "").strip().upper() or None
    except Exception as exc:
        logger.warning("Failed to get current schema: %s", exc)
    return None


def _resolve_database(conn, creds_db: str) -> str:
    """Resolve database: use credential db, or current session db, or fail."""
    db = (creds_db or "").strip().upper()
    if db:
        return db
    # Fallback to current session database
    current = _get_current_database(conn)
    if current:
        logger.info("Using current session database: %s", current)
        return current
    logger.error("No database specified in credentials and no current database in session")
    return ""


def _resolve_schema(conn, creds_schema: str) -> str:
    """Resolve schema: use credential schema, or current session schema, or PUBLIC."""
    schema = (creds_schema or "").strip().upper()
    if schema:
        return schema
    current = _get_current_schema(conn)
    if current:
        logger.info("Using current session schema: %s", current)
        return current
    logger.warning("No schema specified, defaulting to PUBLIC")
    return "PUBLIC"


# ── Metadata Fetching ─────────────────────────────────────────────────────────

def _safe_execute(cur, sql: str, params: tuple = ()) -> list:
    """Execute SQL and return rows, with error handling."""
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    except Exception as exc:
        logger.warning("Query failed: %s | Error: %s", sql[:100], exc)
        return []


def _fetch_table_meta(conn, db: str, schema: str, table: str) -> Optional[TableMeta]:
    """Fetch full metadata for a single table from Snowflake.

    FIXED:
    - Always USE DATABASE and USE SCHEMA before querying
    - Better error messages for permission issues
    - Handle case where table exists in different schema
    - Fetch constraints more robustly
    """
    if not db:
        logger.error("Cannot fetch metadata: no database resolved for table %s", table)
        return None

    if not (_IDENT_RE.match(db) and _IDENT_RE.match(schema) and _IDENT_RE.match(table)):
        logger.warning(
            "Invalid identifier rejected | db=%r schema=%r table=%r",
            db, schema, table,
        )
        return None

    import snowflake.connector

    cur = conn.cursor(snowflake.connector.DictCursor)

    # FIXED: Always set database and schema context
    try:
        cur.execute(f"USE DATABASE {db}")
        cur.execute(f"USE SCHEMA {db}.{schema}")
    except Exception as exc:
        logger.warning("Failed to set database/schema context: %s", exc)
        # Continue anyway - might still work if already in right context

    logger.debug("Fetching metadata | db=%s schema=%s table=%s", db, schema, table)

    # 1. Column types and nullability
    col_rows = _safe_execute(
        cur,
        """
        SELECT column_name, data_type, is_nullable, ordinal_position
        FROM information_schema.columns
        WHERE table_name = %s AND table_schema = %s
        ORDER BY ordinal_position
        """,
        (table, schema),
    )

    if not col_rows:
        # Diagnostic: find which schemas this table name actually lives in
        found_schemas = _safe_execute(
            cur,
            "SELECT DISTINCT table_schema FROM information_schema.columns WHERE table_name = %s",
            (table,),
        )
        if found_schemas:
            schemas = [r.get("TABLE_SCHEMA") or r.get("table_schema") for r in found_schemas]
            logger.warning(
                "Table %s not found in schema %s — found in schema(s): %s. "
                "Check SnowflakeConnectModal schema field.",
                table, schema, schemas,
            )
        else:
            logger.warning(
                "Table %s not found in db=%s at all. "
                "Table may not exist or role lacks SELECT privilege.",
                table, db,
            )
        return None

    # 2. Constraints via SHOW commands (work with standard roles, no REFERENCES privilege needed)
    constraints_map: dict[str, list[str]] = {}

    pk_rows = _safe_execute(cur, f"SHOW PRIMARY KEYS IN {db}.{schema}.{table}")
    for row in pk_rows:
        col = (row.get("column_name") or row.get("COLUMN_NAME") or "").upper()
        if col:
            constraints_map.setdefault(col, []).append("PRIMARY KEY")

    uk_rows = _safe_execute(cur, f"SHOW UNIQUE KEYS IN {db}.{schema}.{table}")
    for row in uk_rows:
        col = (row.get("column_name") or row.get("COLUMN_NAME") or "").upper()
        if col:
            constraints_map.setdefault(col, []).append("UNIQUE")

    columns = []
    for row in col_rows:
        col_name = (row.get("COLUMN_NAME") or row.get("column_name") or "").upper()
        columns.append(ColumnMeta(
            name=col_name,
            data_type=row.get("DATA_TYPE") or row.get("data_type") or "",
            is_nullable=(row.get("IS_NULLABLE") or row.get("is_nullable") or "YES") == "YES",
            constraints=constraints_map.get(col_name, []),
        ))

    # 3. Clustering key + row count from information_schema.tables
    clustering_key: Optional[str] = None
    row_count: Optional[int] = None

    table_info = _safe_execute(
        cur,
        "SELECT clustering_key, row_count FROM information_schema.tables WHERE table_name = %s AND table_schema = %s",
        (table, schema),
    )
    if table_info:
        row = table_info[0]
        clustering_key = row.get("CLUSTERING_KEY") or row.get("clustering_key")
        raw_rc = row.get("ROW_COUNT") or row.get("row_count")
        row_count = int(raw_rc) if raw_rc is not None else None

    # 4. Clustering depth
    clustering_depth: Optional[float] = None
    if clustering_key and db:
        try:
            depth_rows = _safe_execute(
                cur,
                f"SELECT system$clustering_depth('{db}.{schema}.{table}') AS depth"
            )
            if depth_rows:
                val = list(depth_rows[0].values())[0]
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


# ── Main Entry Point ──────────────────────────────────────────────────────────

def fetch_snowflake_context(sql: str) -> SnowflakeContext:
    """
    Parse sql, fetch schema + clustering metadata for all referenced tables.
    Returns SnowflakeContext(available=False) if Snowflake is not connected.
    Never raises — all errors are logged to fetch_errors.
    """
    from ..data import snowflake_connector as sc

    if not sc.is_connected():
        logger.debug("Snowflake not connected — skipping metadata fetch")
        return SnowflakeContext(available=False, tables={})

    tables = _extract_tables(sql)
    logger.info("Agent3/SnowflakeContext START | tables_found=%s", tables)

    if not tables:
        return SnowflakeContext(available=True, tables={}, requested_tables=[])

    conn = sc._conn
    if conn is None:
        logger.warning("Conn became None after is_connected() — degrading gracefully")
        return SnowflakeContext(available=False, tables={})

    # FIXED: Resolve database and schema properly
    creds = sc._creds or {}
    db = _resolve_database(conn, creds.get("database") or "")
    schema = _resolve_schema(conn, creds.get("schema_name") or "")

    if not db:
        logger.error("Cannot fetch metadata: no database available. "
                     "Please specify database in Snowflake credentials.")
        return SnowflakeContext(
            available=False, 
            tables={},
            fetch_errors=["No database specified in credentials or session"],
            requested_tables=tables,
        )

    # Cache management
    global _cache_connection_key
    connection_key = f"{db}.{schema}"
    if connection_key != _cache_connection_key:
        logger.debug("Connection key changed (%r → %r) — cache cleared", 
                     _cache_connection_key, connection_key)
        _cache.clear()
        _cache_connection_key = connection_key

    result: dict[str, TableMeta] = {}
    errors: list[str] = []
    now = time.monotonic()

    for table in tables:
        cache_key = f"{db}.{schema}.{table}"

        # Check cache
        if cache_key in _cache:
            meta, fetched_at = _cache[cache_key]
            if now - fetched_at < _TTL_SECONDS:
                logger.debug("Cache hit | table=%s | age=%.1fs", cache_key, now - fetched_at)
                result[table] = meta
                continue

        try:
            meta = _fetch_table_meta(conn, db, schema, table)
            if meta is None:
                errors.append(f"Could not fetch metadata for table: {table} (not found in {db}.{schema})")
                logger.warning("Table not found | table=%s in %s.%s", table, db, schema)
                continue

            logger.debug(
                "Fetched | table=%s | cols=%d | clustering_key=%r | row_count=%s | constraints=%s",
                table, len(meta.columns), meta.clustering_key, meta.row_count,
                {c.name: c.constraints for c in meta.columns if c.constraints},
            )
            _cache[cache_key] = (meta, time.monotonic())
            result[table] = meta

        except Exception as exc:
            errors.append(f"Error fetching {table}: {exc}")
            logger.exception("Fetch error | table=%s | error=%s", table, exc)

    logger.info(
        "Agent3/SnowflakeContext DONE | requested=%s | fetched=%s | errors=%s",
        tables, list(result.keys()), errors or "none",
    )

    return SnowflakeContext(
        available=True, 
        tables=result, 
        fetch_errors=errors,
        requested_tables=tables,
        resolved_db=db,
        resolved_schema=schema,
    )


# ── Context Block Builder ─────────────────────────────────────────────────────

def build_context_block(sf_context: SnowflakeContext, strict: bool = False) -> str:
    """
    Render SnowflakeContext as a text block for injection into agent system prompts.
    strict=True emits a hard constraint header for the optimizer; False emits informational header for advisor.
    Returns empty string when not available or no tables fetched.

    FIXED: Includes fetch_errors and missing tables in the context so agents know what's incomplete.
    """
    if not sf_context.available:
        return (
            "NOTE: Snowflake metadata is currently unavailable. "
            "Schema-aware suggestions cannot be verified against the actual database."
        )

    if not sf_context.tables:
        if sf_context.fetch_errors:
            return (
                "NOTE: Snowflake metadata fetch returned errors. "
                f"Errors: {'; '.join(sf_context.fetch_errors)}. "
                "Schema-aware suggestions cannot be verified."
            )
        return ""

    if strict:
        header = (
            "STRICT SCHEMA CONSTRAINT — THIS IS AUTHORITATIVE:\n"
            "The schema below is the ONLY valid reference for column and table names. Rules:\n"
            "1. ONLY use column names that appear in this schema.\n"
            "2. NEVER invent, guess, or introduce columns not listed here.\n"
            "3. If a suggestion requires a column absent from this schema, skip that suggestion.\n"
            "4. Preserve all original column names exactly as they appear.\n"
            "Verified Snowflake Schema (authoritative — do not deviate):"
        )
    else:
        header = "Snowflake Metadata (fetched live — use this to validate your suggestions):"

    lines = [header]

    # Add warning about missing tables
    missing_tables = set(sf_context.requested_tables) - set(sf_context.tables.keys())
    if missing_tables:
        lines.append(f"WARNING: Could not fetch metadata for tables: {', '.join(sorted(missing_tables))}")
        if sf_context.fetch_errors:
            lines.append(f"Fetch errors: {'; '.join(sf_context.fetch_errors[:3])}")

    for table_name, meta in sf_context.tables.items():
        lines.append(f"Table: {table_name}")
        if meta.columns:
            col_parts = []
            for col in meta.columns:
                nullable = "NOT NULL" if not col.is_nullable else "nullable"
                tags = [col.data_type, nullable]
                if col.constraints:
                    tags.append(f"constraints: {', '.join(col.constraints)}")
                col_parts.append(f"{col.name} ({', '.join(tags)})")
            lines.append(f"  Columns: {', '.join(col_parts)}")
        else:
            lines.append("  Columns: (no columns fetched)")

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


# ── Schema Validation ─────────────────────────────────────────────────────────

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

    known: set[str] = set()
    for meta in sf_context.tables.values():
        for col in meta.columns:
            known.add(col.name.upper())

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


# ── Query History Helpers ─────────────────────────────────────────────────────

def find_recent_query_run(conn, sql_text: str) -> Optional[str]:
    """
    Search INFORMATION_SCHEMA.QUERY_HISTORY for a recent successful run of sql_text.
    Returns the QUERY_ID string, or None if not found.
    """
    from ..data import snowflake_connector as sc
    import snowflake.connector

    fingerprint = " ".join(sql_text.split())[:500]
    search_fragment = fingerprint[:100].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    creds = sc._creds or {}
    db = _resolve_database(conn, creds.get("database") or "")

    cur = conn.cursor(snowflake.connector.DictCursor)
    if db and _IDENT_RE.match(db):
        cur.execute(f"USE DATABASE {db}")

    rows = _safe_execute(
        cur,
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

    if rows:
        return rows[0].get("QUERY_ID") or rows[0].get("query_id")
    return None


def fetch_query_kpis(conn, query_id: str, source: str = "history") -> "QueryKPIs":
    """
    Fetch execution metrics for a specific query_id from INFORMATION_SCHEMA.QUERY_HISTORY.
    """
    from ..models.kpi_models import QueryKPIs
    from ..data import snowflake_connector as sc
    import snowflake.connector

    creds = sc._creds or {}
    db = _resolve_database(conn, creds.get("database") or "")

    cur = conn.cursor(snowflake.connector.DictCursor)
    if db and _IDENT_RE.match(db):
        cur.execute(f"USE DATABASE {db}")

    rows = _safe_execute(
        cur,
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

    if not rows:
        return QueryKPIs(
            query_id=query_id,
            elapsed_ms=None, bytes_scanned=None,
            bytes_spilled_local=None, bytes_spilled_remote=None,
            partitions_scanned=None, partitions_total=None,
            rows_produced=None, credits=None,
            source=source,
            error=f"Query ID {query_id!r} not found in INFORMATION_SCHEMA.QUERY_HISTORY",
        )

    row = rows[0]

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