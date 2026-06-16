# Agent 3 — Snowflake Context Fetcher Design

## Overview

Agent 3 is a pure-Python metadata prefetcher that runs before Agent 1 on every analyze/optimize request. It parses the incoming SQL query, extracts referenced table names, fetches live schema and clustering metadata from Snowflake, and returns a `SnowflakeContext` object that both Agent 1 and Agent 2 consume via prompt injection.

**Key constraint:** If Snowflake is not connected, Agent 3 returns `SnowflakeContext(available=False)` and the system behaves exactly as today — zero regression.

---

## Architecture

```
SQL query + strategy tier (from HITL)
           │
           ▼
    ┌─────────────┐
    │   Agent 3   │  sqlglot parses SQL → extracts table names
    │  prefetch   │  fires information_schema + clustering queries
    │             │  TTL-cached per table (300s)
    └──────┬──────┘
           │ SnowflakeContext
           ▼
    ┌─────────────┐
    │   Agent 1   │  advisor.py — context injected into system prompt suffix
    │  (advisor)  │
    └──────┬──────┘
           │ suggestions + SnowflakeContext (passed through)
           ▼
    ┌─────────────┐
    │   Agent 2   │  optimizer.py — same context validates rewrites
    │ (optimizer) │
    └─────────────┘
```

---

## Graceful Degradation

| State | Behavior |
|---|---|
| Snowflake not connected | `SnowflakeContext(available=False)` — no fetches, no prompt injection |
| Connected, table not in schema | Skip that table, log to `fetch_errors`, continue |
| `system$clustering_depth()` returns NULL | `TableMeta.clustering_depth = None`, rest of meta still returned |
| Any query throws | Catch, log to `fetch_errors`, omit that table's `TableMeta` |
| `sqlglot` parse fails | `tables={}`, `available=True` — agents get no metadata block but don't fail |

Errors surface as `"snowflake_context_errors": [...]` in API response for debugging. Never block analysis.

---

## Data Models

```python
from dataclasses import dataclass, field

@dataclass
class ColumnMeta:
    name: str
    data_type: str
    is_nullable: bool
    constraints: list[str]          # e.g. ['PRIMARY KEY'], ['FOREIGN KEY', 'UNIQUE']

@dataclass
class TableMeta:
    columns: list[ColumnMeta]
    clustering_key: str | None      # e.g. "(DATE_TRUNC('month', CREATED_AT))"
    clustering_depth: float | None  # from system$clustering_depth(); lower = better clustered
    row_count: int | None

@dataclass
class SnowflakeContext:
    available: bool                 # False = not connected, skip prompt injection
    tables: dict[str, TableMeta]    # key = uppercase table name
    fetch_errors: list[str] = field(default_factory=list)
```

---

## Files

### New
- `backend/agents/snowflake_context.py` — `SnowflakeFetcher` class + dataclasses above
- `backend/tests/test_snowflake_context.py` — 7 tests, all with mocked connector

### Modified
- `backend/agents/advisor.py` — accept `sf_context: SnowflakeContext`, inject metadata block into prompt suffix
- `backend/agents/optimizer.py` — same
- `backend/api/routes.py` — call `fetch_snowflake_context(sql)` before Agent 1 on `/analyze`, `/optimize`, `/analyze-custom`, `/optimize-custom`

### Not modified
- `backend/data/snowflake_connector.py` — Agent 3 reads `_conn`, `_creds`, `is_connected()` from here; no changes to connection management

---

## SnowflakeFetcher

### SQL Parsing

```python
import sqlglot
from sqlglot import exp

def _extract_tables(sql: str) -> list[str]:
    try:
        tree = sqlglot.parse_one(sql, dialect="snowflake")
        return list({t.name.upper() for t in tree.find_all(exp.Table) if t.name})
    except Exception:
        return []
```

Handles CTEs, subqueries, aliases. Returns deduplicated uppercase table names.

### TTL Cache

```python
_cache: dict[str, tuple[TableMeta, float]] = {}  # key = "SCHEMA.TABLE"
_TTL_SECONDS = 300
```

Module-level singleton. Key format: `"<SCHEMA>.<TABLE>"` (uppercase). Cache stores `(TableMeta, fetched_at_unix_timestamp)`. Expired entries re-fetched on next call.

### Per-Table Snowflake Queries

For each table not in cache (or expired), Agent 3 runs 4 sequential queries against `_conn`:

```sql
-- 1. Column types and nullability
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = '<TABLE>' AND table_schema = '<SCHEMA>'
ORDER BY ordinal_position;

-- 2. Constraints (PK, UNIQUE, FK)
SELECT kcu.column_name, tc.constraint_type
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_name = '<TABLE>' AND tc.table_schema = '<SCHEMA>';

-- 3. Clustering key and row count
SELECT clustering_key, row_count
FROM information_schema.tables
WHERE table_name = '<TABLE>' AND table_schema = '<SCHEMA>';

-- 4. Clustering depth
SELECT system$clustering_depth('<DB>.<SCHEMA>.<TABLE>');
```

Schema and DB are sourced from `_creds` already stored in `snowflake_connector`.

### Public Interface

```python
def fetch_snowflake_context(sql: str) -> SnowflakeContext:
    """
    Parse sql, fetch metadata for all referenced tables.
    Returns SnowflakeContext(available=False) if not connected.
    Never raises — all errors logged to fetch_errors.
    """
```

Called synchronously from routes.py before `await run_advisor_agent_async(...)`.

---

## Prompt Injection

When `sf_context.available = True` and `sf_context.tables` is non-empty, both agents receive this block appended to their system prompt:

```
Snowflake Metadata (fetched live — use this to validate your suggestions):

Table: ORDERS
  Columns: ORDER_ID (NUMBER, NOT NULL [PRIMARY KEY]), CUSTOMER_ID (NUMBER, NOT NULL),
           CREATED_AT (TIMESTAMP_NTZ, NOT NULL), STATUS (VARCHAR, nullable)
  Clustering Key: (DATE_TRUNC('month', CREATED_AT))
  Clustering Depth: 0.83  ← values > 0.7 indicate poor clustering; many micro-partitions to scan
  Row Count: 48,200,000

Table: CUSTOMERS
  Columns: CUSTOMER_ID (NUMBER, NOT NULL [PRIMARY KEY]), EMAIL (VARCHAR, NOT NULL [UNIQUE]),
           REGION (VARCHAR, nullable)
  Clustering Key: none
  Row Count: 2,100,000
```

**Agent 1 uses metadata to:**
- Skip clustering suggestions where depth already low (well-clustered)
- Flag `IS NULL` predicates on `NOT NULL` columns (always false — dead filter)
- Identify FK relationships as join elimination candidates
- Weight partition pruning suggestions by actual row count

**Agent 2 uses metadata to:**
- Confirm CAST rewrites match actual column data types before applying
- Validate correlated subquery rewrites against column nullability
- Skip ORDER BY elimination when clustering key implies existing sort order dependency

When `available = False` → block not appended → identical to current behavior.

---

## Route Integration

```python
# routes.py — /analyze (same pattern for /optimize, /analyze-custom, /optimize-custom)
from ..agents.snowflake_context import fetch_snowflake_context

@router.post("/analyze")
async def analyze_query(request: AnalyzeRequest):
    ...
    query_data = get_query(request.query_id)

    # Agent 3: prefetch (sync, non-blocking on failure)
    sf_context = fetch_snowflake_context(query_data["query_text"])

    # Agent 1
    advisor_result = await run_advisor_agent_async(
        client, query_data["query_text"], request.strategy, sf_context
    )
    ...
    return {
        ...,
        "snowflake_context_errors": sf_context.fetch_errors,  # debug only
    }
```

---

## Tests

All tests in `backend/tests/test_snowflake_context.py`. Snowflake connector mocked — no real connection required.

```python
# 1. Not connected → available=False, zero Snowflake queries fired
def test_returns_unavailable_when_not_connected()

# 2. Connected + mock fetch → TableMeta columns/constraints/clustering populated correctly
def test_fetches_column_metadata()

# 3. Cache hit — second call for same table skips Snowflake queries
def test_cache_prevents_duplicate_fetch()

# 4. Cache TTL expired — re-fetches after 300s
def test_cache_expires_after_ttl()

# 5. Table missing from schema → logged to fetch_errors, other tables unaffected
def test_missing_table_logged_to_errors()

# 6. sqlglot extracts tables from CTE + subquery + aliased table correctly
def test_extract_tables_handles_ctes_subqueries_aliases()

# 7. system$clustering_depth returns NULL → TableMeta.clustering_depth is None, no error
def test_null_clustering_depth_handled()
```

---

## Dependencies

Add to `backend/requirements.txt`:
```
sqlglot>=23.0.0
```

`snowflake-connector-python` already present (used by `snowflake_connector.py`).
