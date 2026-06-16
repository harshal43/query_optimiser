# Agent 3 — Snowflake Context Fetcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Agent 3, a Snowflake metadata prefetcher that fetches live schema and clustering context before Agent 1 runs, injecting it into both agents' system prompts to ground optimization suggestions in real DB state.

**Architecture:** `fetch_snowflake_context(sql)` parses table names from SQL via sqlglot, fetches column types + constraints + clustering metadata from `information_schema` and `system$clustering_depth()`, caches per table with 300 s TTL, and returns a `SnowflakeContext` dataclass. Both agents receive a `sf_context` keyword argument; when `available=True` they prepend a metadata block to their system prompts. When Snowflake is not connected, `available=False` and agents behave identically to today — zero regression.

**Tech Stack:** Python 3.14, FastAPI, sqlglot (Snowflake dialect), snowflake-connector-python (existing), pytest, unittest.mock

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/requirements.txt` | Modify | Add `sqlglot>=23.0.0` |
| `backend/agents/snowflake_context.py` | Create | Dataclasses, `_extract_tables`, `_fetch_table_meta`, TTL cache, `fetch_snowflake_context`, `build_context_block` |
| `backend/tests/test_snowflake_context.py` | Create | All Agent 3 unit tests (mocked connector) |
| `backend/agents/advisor.py` | Modify | Add `sf_context` param; inject `build_context_block` into system prompt |
| `backend/agents/optimizer.py` | Modify | Same as advisor |
| `backend/api/routes.py` | Modify | Call `fetch_snowflake_context` before Agent 1 on 4 endpoints; add `snowflake_context_errors` to responses |

---

### Task 1: Data Models + SQL Table Extraction

**Files:**
- Create: `backend/agents/snowflake_context.py`
- Create: `backend/tests/test_snowflake_context.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add sqlglot to requirements.txt**

Open `backend/requirements.txt` and add this line:
```
sqlglot>=23.0.0
```

- [ ] **Step 2: Install sqlglot**

```bash
pip install "sqlglot>=23.0.0"
```

Expected: `Successfully installed sqlglot-<version>`

- [ ] **Step 3: Write failing tests**

Create `backend/tests/test_snowflake_context.py`:

```python
import pytest
from backend.agents.snowflake_context import (
    _extract_tables,
    SnowflakeContext,
    TableMeta,
    ColumnMeta,
)


def test_extract_tables_simple():
    result = _extract_tables("SELECT * FROM orders WHERE id = 1")
    assert result == ["ORDERS"]


def test_extract_tables_join():
    sql = "SELECT o.id FROM orders o JOIN customers c ON o.customer_id = c.id"
    assert set(_extract_tables(sql)) == {"ORDERS", "CUSTOMERS"}


def test_extract_tables_cte():
    sql = """
    WITH recent AS (SELECT * FROM orders WHERE created_at > '2024-01-01')
    SELECT * FROM recent JOIN customers c ON recent.customer_id = c.id
    """
    result = set(_extract_tables(sql))
    assert "ORDERS" in result
    assert "CUSTOMERS" in result


def test_extract_tables_parse_failure_returns_empty_list():
    result = _extract_tables("NOT VALID SQL !!!@#$%")
    assert isinstance(result, list)


def test_snowflake_context_defaults():
    ctx = SnowflakeContext(available=False, tables={})
    assert ctx.available is False
    assert ctx.tables == {}
    assert ctx.fetch_errors == []


def test_table_meta_fields():
    meta = TableMeta(columns=[], clustering_key=None, clustering_depth=None, row_count=None)
    assert meta.columns == []
    assert meta.clustering_key is None
    assert meta.clustering_depth is None
    assert meta.row_count is None


def test_column_meta_fields():
    col = ColumnMeta(name="ORDER_ID", data_type="NUMBER", is_nullable=False, constraints=["PRIMARY KEY"])
    assert col.name == "ORDER_ID"
    assert col.is_nullable is False
    assert "PRIMARY KEY" in col.constraints
```

- [ ] **Step 4: Run tests — verify they fail**

```bash
python -m pytest backend/tests/test_snowflake_context.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `snowflake_context.py` does not exist yet.

- [ ] **Step 5: Create backend/agents/snowflake_context.py with dataclasses and _extract_tables**

```python
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
```

- [ ] **Step 6: Run tests — verify they pass**

```bash
python -m pytest backend/tests/test_snowflake_context.py -v
```

Expected: `7 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/agents/snowflake_context.py backend/tests/test_snowflake_context.py backend/requirements.txt
git commit -m "feat: add SnowflakeContext dataclasses and _extract_tables (Agent 3 Task 1)"
```

---

### Task 2: Per-Table Snowflake Fetcher

**Files:**
- Modify: `backend/agents/snowflake_context.py`
- Modify: `backend/tests/test_snowflake_context.py`

- [ ] **Step 1: Add _fetch_table_meta to the import line in the test file**

Update the import block at the top of `backend/tests/test_snowflake_context.py`:

```python
from unittest.mock import MagicMock

from backend.agents.snowflake_context import (
    _extract_tables,
    _fetch_table_meta,
    SnowflakeContext,
    TableMeta,
    ColumnMeta,
)
```

- [ ] **Step 2: Add failing tests for _fetch_table_meta**

Append to `backend/tests/test_snowflake_context.py`:

```python
# ── _fetch_table_meta helpers ─────────────────────────────────────────────────

def _make_mock_conn(col_rows, constraint_rows, table_row, depth_row):
    """Build a mock snowflake connection whose cursor replays the given rows."""
    cursor = MagicMock()
    cursor.fetchall.side_effect = [col_rows, constraint_rows]
    cursor.fetchone.side_effect = [table_row, depth_row]
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn


def test_fetch_table_meta_populates_columns():
    col_rows = [
        {"COLUMN_NAME": "ORDER_ID", "DATA_TYPE": "NUMBER",  "IS_NULLABLE": "NO"},
        {"COLUMN_NAME": "STATUS",   "DATA_TYPE": "VARCHAR", "IS_NULLABLE": "YES"},
    ]
    constraint_rows = [{"COLUMN_NAME": "ORDER_ID", "CONSTRAINT_TYPE": "PRIMARY KEY"}]
    table_row = {"CLUSTERING_KEY": "(CREATED_AT)", "ROW_COUNT": 1_000_000}
    depth_row  = {"DEPTH": 0.85}

    conn = _make_mock_conn(col_rows, constraint_rows, table_row, depth_row)
    meta = _fetch_table_meta(conn, "MYDB", "PUBLIC", "ORDERS")

    assert len(meta.columns) == 2
    assert meta.columns[0].name == "ORDER_ID"
    assert meta.columns[0].data_type == "NUMBER"
    assert meta.columns[0].is_nullable is False
    assert meta.columns[0].constraints == ["PRIMARY KEY"]
    assert meta.columns[1].name == "STATUS"
    assert meta.columns[1].is_nullable is True
    assert meta.clustering_key == "(CREATED_AT)"
    assert meta.row_count == 1_000_000
    assert meta.clustering_depth == pytest.approx(0.85)


def test_fetch_table_meta_null_clustering_depth():
    col_rows = [{"COLUMN_NAME": "ID", "DATA_TYPE": "NUMBER", "IS_NULLABLE": "NO"}]
    table_row = {"CLUSTERING_KEY": None, "ROW_COUNT": 500}
    conn = _make_mock_conn(col_rows, [], table_row, None)
    meta = _fetch_table_meta(conn, "MYDB", "PUBLIC", "SMALL")
    assert meta.clustering_depth is None


def test_fetch_table_meta_returns_none_for_missing_table():
    conn = _make_mock_conn([], [], None, None)
    result = _fetch_table_meta(conn, "MYDB", "PUBLIC", "GHOST")
    assert result is None
```

- [ ] **Step 3: Run new tests — verify they fail**

```bash
python -m pytest backend/tests/test_snowflake_context.py::test_fetch_table_meta_populates_columns -v
```

Expected: `ImportError: cannot import name '_fetch_table_meta'`

- [ ] **Step 4: Implement _fetch_table_meta in snowflake_context.py**

Add after `_extract_tables`:

```python
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
```

- [ ] **Step 5: Run all tests — verify they pass**

```bash
python -m pytest backend/tests/test_snowflake_context.py -v
```

Expected: `10 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/agents/snowflake_context.py backend/tests/test_snowflake_context.py
git commit -m "feat: add _fetch_table_meta with column, constraint and clustering queries (Agent 3 Task 2)"
```

---

### Task 3: TTL Cache + fetch_snowflake_context

**Files:**
- Modify: `backend/agents/snowflake_context.py`
- Modify: `backend/tests/test_snowflake_context.py`

- [ ] **Step 1: Update imports in test file**

Update the import block at the top of `backend/tests/test_snowflake_context.py`:

```python
import time
from unittest.mock import MagicMock, patch

import backend.agents.snowflake_context as sc_module
from backend.agents.snowflake_context import (
    _extract_tables,
    _fetch_table_meta,
    fetch_snowflake_context,
    SnowflakeContext,
    TableMeta,
    ColumnMeta,
)
```

- [ ] **Step 2: Add failing tests**

Append to `backend/tests/test_snowflake_context.py`:

```python
# ── fetch_snowflake_context ───────────────────────────────────────────────────

def test_returns_unavailable_when_not_connected():
    with patch("backend.data.snowflake_connector.is_connected", return_value=False):
        ctx = fetch_snowflake_context("SELECT * FROM orders")
    assert ctx.available is False
    assert ctx.tables == {}
    assert ctx.fetch_errors == []


def test_missing_table_logged_to_fetch_errors():
    cursor = MagicMock()
    cursor.fetchall.return_value = []   # empty = table not in schema
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = cursor

    with patch("backend.data.snowflake_connector.is_connected", return_value=True), \
         patch("backend.data.snowflake_connector._conn", mock_conn), \
         patch("backend.data.snowflake_connector._creds", {"database": "DB", "schema_name": "PUBLIC"}):
        ctx = fetch_snowflake_context("SELECT * FROM ghost_table")

    assert ctx.available is True
    assert "GHOST_TABLE" not in ctx.tables
    assert any("GHOST_TABLE" in e for e in ctx.fetch_errors)


def test_cache_prevents_duplicate_fetch():
    sc_module._cache.clear()

    col_rows = [{"COLUMN_NAME": "ID", "DATA_TYPE": "NUMBER", "IS_NULLABLE": "NO"}]
    cursor = MagicMock()
    cursor.fetchall.side_effect = [col_rows, []]           # columns, constraints
    cursor.fetchone.side_effect = [
        {"CLUSTERING_KEY": None, "ROW_COUNT": 100}, None  # table row, depth
    ]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = cursor

    with patch("backend.data.snowflake_connector.is_connected", return_value=True), \
         patch("backend.data.snowflake_connector._conn", mock_conn), \
         patch("backend.data.snowflake_connector._creds", {"database": "DB", "schema_name": "PUBLIC"}):
        fetch_snowflake_context("SELECT * FROM orders")
        fetch_snowflake_context("SELECT * FROM orders")  # cache hit

    # cursor was created only once (only one _fetch_table_meta call)
    assert mock_conn.cursor.call_count == 1


def test_cache_expires_after_ttl():
    sc_module._cache.clear()

    # Pre-seed an expired entry
    stale_meta = TableMeta(columns=[], clustering_key=None, clustering_depth=None, row_count=None)
    expired_ts = time.monotonic() - sc_module._TTL_SECONDS - 1
    sc_module._cache["PUBLIC.ORDERS"] = (stale_meta, expired_ts)

    col_rows = [{"COLUMN_NAME": "ID", "DATA_TYPE": "NUMBER", "IS_NULLABLE": "NO"}]
    cursor = MagicMock()
    cursor.fetchall.side_effect = [col_rows, []]
    cursor.fetchone.side_effect = [{"CLUSTERING_KEY": None, "ROW_COUNT": 50}, None]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = cursor

    with patch("backend.data.snowflake_connector.is_connected", return_value=True), \
         patch("backend.data.snowflake_connector._conn", mock_conn), \
         patch("backend.data.snowflake_connector._creds", {"database": "DB", "schema_name": "PUBLIC"}):
        fetch_snowflake_context("SELECT * FROM orders")

    # Expired entry should have been re-fetched
    assert mock_conn.cursor.call_count >= 1
```

- [ ] **Step 3: Run new tests — verify they fail**

```bash
python -m pytest backend/tests/test_snowflake_context.py::test_returns_unavailable_when_not_connected -v
```

Expected: `ImportError: cannot import name 'fetch_snowflake_context'`

- [ ] **Step 4: Add fetch_snowflake_context to snowflake_context.py**

Add after `_fetch_table_meta`:

```python
def fetch_snowflake_context(sql: str) -> SnowflakeContext:
    """
    Parse sql, fetch schema + clustering metadata for all referenced tables.
    Returns SnowflakeContext(available=False) if Snowflake is not connected.
    Never raises — all errors are logged to fetch_errors.
    """
    from ..data import snowflake_connector as sc

    if not sc.is_connected():
        return SnowflakeContext(available=False, tables={})

    tables = _extract_tables(sql)
    if not tables:
        return SnowflakeContext(available=True, tables={})

    creds = sc._creds or {}
    db = (creds.get("database") or "").upper()
    schema = (creds.get("schema_name") or "PUBLIC").upper()
    conn = sc._conn

    result: dict[str, TableMeta] = {}
    errors: list[str] = []
    now = time.monotonic()

    for table in tables:
        cache_key = f"{schema}.{table}"
        if cache_key in _cache:
            meta, fetched_at = _cache[cache_key]
            if now - fetched_at < _TTL_SECONDS:
                result[table] = meta
                continue

        try:
            meta = _fetch_table_meta(conn, db, schema, table)
            if meta is None:
                errors.append(f"Table not found in schema: {table}")
                continue
            _cache[cache_key] = (meta, now)
            result[table] = meta
        except Exception as exc:
            errors.append(f"Error fetching {table}: {exc}")

    return SnowflakeContext(available=True, tables=result, fetch_errors=errors)
```

- [ ] **Step 5: Run all tests — verify they pass**

```bash
python -m pytest backend/tests/test_snowflake_context.py -v
```

Expected: `14 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/agents/snowflake_context.py backend/tests/test_snowflake_context.py
git commit -m "feat: add fetch_snowflake_context with TTL cache (Agent 3 Task 3)"
```

---

### Task 4: build_context_block Prompt Helper

**Files:**
- Modify: `backend/agents/snowflake_context.py`
- Modify: `backend/tests/test_snowflake_context.py`

- [ ] **Step 1: Update imports in test file**

Update the import block:

```python
import time
from unittest.mock import MagicMock, patch

import backend.agents.snowflake_context as sc_module
from backend.agents.snowflake_context import (
    _extract_tables,
    _fetch_table_meta,
    fetch_snowflake_context,
    build_context_block,
    SnowflakeContext,
    TableMeta,
    ColumnMeta,
)
```

- [ ] **Step 2: Add failing tests**

Append to `backend/tests/test_snowflake_context.py`:

```python
# ── build_context_block ───────────────────────────────────────────────────────

def _make_context(tables: dict) -> SnowflakeContext:
    return SnowflakeContext(available=True, tables=tables)


def test_build_context_block_empty_when_not_available():
    ctx = SnowflakeContext(available=False, tables={})
    assert build_context_block(ctx) == ""


def test_build_context_block_empty_when_no_tables():
    ctx = SnowflakeContext(available=True, tables={})
    assert build_context_block(ctx) == ""


def test_build_context_block_contains_metadata():
    meta = TableMeta(
        columns=[
            ColumnMeta("ORDER_ID", "NUMBER",  False, ["PRIMARY KEY"]),
            ColumnMeta("STATUS",   "VARCHAR", True,  []),
        ],
        clustering_key="(CREATED_AT)",
        clustering_depth=0.83,
        row_count=1_000_000,
    )
    block = build_context_block(_make_context({"ORDERS": meta}))
    assert "ORDERS" in block
    assert "ORDER_ID" in block
    assert "NUMBER" in block
    assert "PRIMARY KEY" in block
    assert "(CREATED_AT)" in block
    assert "0.83" in block
    assert "1,000,000" in block


def test_build_context_block_none_clustering_key():
    meta = TableMeta(columns=[], clustering_key=None, clustering_depth=None, row_count=None)
    block = build_context_block(_make_context({"SMALL": meta}))
    assert "none" in block


def test_build_context_block_high_depth_warns():
    meta = TableMeta(columns=[], clustering_key="(X)", clustering_depth=0.9, row_count=None)
    block = build_context_block(_make_context({"BIG": meta}))
    assert "poor clustering" in block or "micro-partition" in block
```

- [ ] **Step 3: Run new tests — verify they fail**

```bash
python -m pytest backend/tests/test_snowflake_context.py::test_build_context_block_contains_metadata -v
```

Expected: `ImportError: cannot import name 'build_context_block'`

- [ ] **Step 4: Add build_context_block to snowflake_context.py**

Add at the bottom of `backend/agents/snowflake_context.py`:

```python
def build_context_block(sf_context: SnowflakeContext) -> str:
    """
    Render SnowflakeContext as a text block for injection into agent system prompts.
    Returns empty string when not available or no tables fetched.
    """
    if not sf_context.available or not sf_context.tables:
        return ""

    lines = ["\nSnowflake Metadata (fetched live — use this to validate your suggestions):"]
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
```

- [ ] **Step 5: Run all tests**

```bash
python -m pytest backend/tests/test_snowflake_context.py -v
```

Expected: `19 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/agents/snowflake_context.py backend/tests/test_snowflake_context.py
git commit -m "feat: add build_context_block prompt injection helper (Agent 3 Task 4)"
```

---

### Task 5: Advisor Integration

**Files:**
- Modify: `backend/agents/advisor.py`

- [ ] **Step 1: Add import to advisor.py**

At the top of `backend/agents/advisor.py`, after the existing imports, add:

```python
from .snowflake_context import SnowflakeContext, build_context_block
```

- [ ] **Step 2: Replace run_advisor_agent_async in advisor.py**

Replace the entire `run_advisor_agent_async` function with:

```python
async def run_advisor_agent_async(
    client: LLMClient,
    query: str,
    strategy: str = "",
    sf_context: SnowflakeContext | None = None,
) -> dict:
    config = load_config()
    system = SYSTEM_PROMPT + _build_advisor_suffix(config, strategy)
    if sf_context is not None:
        system += build_context_block(sf_context)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Analyze the following Snowflake SQL query and provide optimization suggestions.\n\n```sql\n{query}\n```"}
    ]
    response = await client.async_chat(messages, temperature=0.1)
    content = client.extract_content(response)
    usage = client.extract_usage(response)
    raw_usage = usage.pop("raw_usage", {})
    cost_info = calculate_cost(client.model, usage["prompt_tokens"], usage["completion_tokens"])
    return {
        "suggestions_raw": content.strip(),
        "parsed_suggestions": parse_suggestions(content),
        "token_usage": {**cost_info, "raw_usage": raw_usage},
    }
```

- [ ] **Step 3: Replace run_advisor_agent (sync) in advisor.py**

Replace the entire `run_advisor_agent` function with:

```python
def run_advisor_agent(
    client: LLMClient,
    query: str,
    strategy: str = "",
    sf_context: SnowflakeContext | None = None,
) -> dict:
    config = load_config()
    system = SYSTEM_PROMPT + _build_advisor_suffix(config, strategy)
    if sf_context is not None:
        system += build_context_block(sf_context)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Analyze the following Snowflake SQL query and provide optimization suggestions.\n\n```sql\n{query}\n```"}
    ]
    response = client.chat(messages, temperature=0.1)
    content = client.extract_content(response)
    usage = client.extract_usage(response)
    raw_usage = usage.pop("raw_usage", {})
    cost_info = calculate_cost(client.model, usage["prompt_tokens"], usage["completion_tokens"])
    return {
        "suggestions_raw": content.strip(),
        "parsed_suggestions": parse_suggestions(content),
        "token_usage": {**cost_info, "raw_usage": raw_usage},
    }
```

- [ ] **Step 4: Run full test suite — verify no regression**

```bash
python -m pytest backend/tests/ -v
```

Expected: `28 passed` (existing) `+ 19 passed` (snowflake_context) = all pass. `sf_context` defaults to `None` so existing tests are unaffected.

- [ ] **Step 5: Commit**

```bash
git add backend/agents/advisor.py
git commit -m "feat: inject SnowflakeContext into advisor agent system prompt (Agent 3 Task 5)"
```

---

### Task 6: Optimizer Integration

**Files:**
- Modify: `backend/agents/optimizer.py`

- [ ] **Step 1: Add import to optimizer.py**

At the top of `backend/agents/optimizer.py`, after the existing imports, add:

```python
from .snowflake_context import SnowflakeContext, build_context_block
```

- [ ] **Step 2: Replace run_optimizer_agent_async in optimizer.py**

Replace the entire `run_optimizer_agent_async` function with:

```python
async def run_optimizer_agent_async(
    client: LLMClient,
    original_query: str,
    suggestions: str,
    strategy: str = "",
    sf_context: SnowflakeContext | None = None,
) -> dict:
    config = load_config()
    system = SYSTEM_PROMPT + _build_optimizer_suffix(config, strategy)
    if sf_context is not None:
        system += build_context_block(sf_context)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Original Snowflake SQL query:\n```sql\n{original_query}\n```\n\nOptimization suggestions:\n{suggestions}\n\nProduce the optimized query, explain all changes, and estimate credit savings."}
    ]
    response = await client.async_chat(messages, temperature=0.1)
    content = client.extract_content(response)
    usage = client.extract_usage(response)
    raw_usage = usage.pop("raw_usage", {})
    cost_info = calculate_cost(client.model, usage["prompt_tokens"], usage["completion_tokens"])
    return {
        "optimized_query": extract_sql(content),
        "explanation": extract_explanation(content),
        "credit_savings": extract_credit_savings(content),
        "change_summary": extract_change_summary(content),
        "raw_response": content,
        "token_usage": {**cost_info, "raw_usage": raw_usage},
    }
```

- [ ] **Step 3: Replace run_optimizer_agent (sync) in optimizer.py**

Replace the entire `run_optimizer_agent` function with:

```python
def run_optimizer_agent(
    client: LLMClient,
    original_query: str,
    suggestions: str,
    strategy: str = "",
    sf_context: SnowflakeContext | None = None,
) -> dict:
    config = load_config()
    system = SYSTEM_PROMPT + _build_optimizer_suffix(config, strategy)
    if sf_context is not None:
        system += build_context_block(sf_context)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Original Snowflake SQL query:\n```sql\n{original_query}\n```\n\nOptimization suggestions:\n{suggestions}\n\nProduce the optimized query, explain all changes, and estimate credit savings."}
    ]
    response = client.chat(messages, temperature=0.1)
    content = client.extract_content(response)
    usage = client.extract_usage(response)
    raw_usage = usage.pop("raw_usage", {})
    cost_info = calculate_cost(client.model, usage["prompt_tokens"], usage["completion_tokens"])
    return {
        "optimized_query": extract_sql(content),
        "explanation": extract_explanation(content),
        "credit_savings": extract_credit_savings(content),
        "change_summary": extract_change_summary(content),
        "raw_response": content,
        "token_usage": {**cost_info, "raw_usage": raw_usage},
    }
```

- [ ] **Step 4: Run full test suite**

```bash
python -m pytest backend/tests/ -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add backend/agents/optimizer.py
git commit -m "feat: inject SnowflakeContext into optimizer agent system prompt (Agent 3 Task 6)"
```

---

### Task 7: Route Integration + Full Regression

**Files:**
- Modify: `backend/api/routes.py`

- [ ] **Step 1: Add import to routes.py**

At the top of `backend/api/routes.py`, after the existing agent imports, add:

```python
from ..agents.snowflake_context import fetch_snowflake_context
```

- [ ] **Step 2: Modify the /analyze route**

Replace the entire `analyze_query` function with:

```python
@router.post("/analyze")
async def analyze_query(request: AnalyzeRequest):
    if request.model not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{request.model}' not supported. Choose from: {SUPPORTED_MODELS}",
        )
    try:
        query_data = get_query(request.query_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    try:
        creds = get_llm_credentials(request.model)
        client = LLMClient(api_key=creds["api_key"], base_url=creds["base_url"], model=request.model)
        sf_context = fetch_snowflake_context(query_data["query_text"])
        advisor_result = await run_advisor_agent_async(
            client, query_data["query_text"], request.strategy, sf_context
        )
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Advisor agent failed: {exc}")

    return {
        "query_id": request.query_id,
        "original_query": query_data["query_text"],
        "credits": query_data["credits"],
        "suggestions_raw": advisor_result["suggestions_raw"],
        "parsed_suggestions": advisor_result["parsed_suggestions"],
        "snowflake_context_errors": sf_context.fetch_errors,
    }
```

- [ ] **Step 3: Modify the /optimize route**

Replace the entire `optimize_query` function with:

```python
@router.post("/optimize")
async def optimize_query(request: OptimizeRequest):
    if request.model not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{request.model}' not supported. Choose from: {SUPPORTED_MODELS}",
        )
    if not request.selected_suggestions:
        raise HTTPException(
            status_code=400,
            detail="No suggestions selected. Please select at least one suggestion.",
        )
    try:
        query_data = get_query(request.query_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    original_query: str = query_data["query_text"]
    credits: float = query_data["credits"]
    selected_text = "\n\n".join(request.selected_suggestions)

    try:
        creds = get_llm_credentials(request.model)
        client = LLMClient(api_key=creds["api_key"], base_url=creds["base_url"], model=request.model)
        sf_context = fetch_snowflake_context(original_query)
        optimizer_result = await run_optimizer_agent_async(
            client, original_query, selected_text, request.strategy, sf_context
        )
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Optimizer agent failed: {exc}")

    savings = optimizer_result.get("credit_savings", {})
    savings_pct = savings.get("percentage", 0.0)
    estimated_optimized_credits = round(credits * (1 - savings_pct / 100), 6)
    credits_saved = round(credits - estimated_optimized_credits, 6)

    return {
        "query_id": request.query_id,
        "original_query": original_query,
        "optimizer_result": optimizer_result,
        "cost_comparison": {
            "original_credits": credits,
            "estimated_optimized_credits": estimated_optimized_credits,
            "credits_saved": credits_saved,
            "savings_percentage": round(savings_pct, 2),
            "savings_reasoning": savings.get("reasoning", ""),
        },
        "snowflake_context_errors": sf_context.fetch_errors,
    }
```

- [ ] **Step 4: Modify the /analyze-custom route**

Replace the entire `analyze_custom_query` function with:

```python
@router.post("/analyze-custom")
async def analyze_custom_query(request: AnalyzeCustomRequest):
    if request.model not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{request.model}' not supported. Choose from: {SUPPORTED_MODELS}",
        )
    if not request.query_text.strip():
        raise HTTPException(status_code=400, detail="query_text must not be empty.")

    try:
        creds = get_llm_credentials(request.model)
        client = LLMClient(api_key=creds["api_key"], base_url=creds["base_url"], model=request.model)
        sf_context = fetch_snowflake_context(request.query_text)
        advisor_result = await run_advisor_agent_async(
            client, request.query_text, request.strategy, sf_context
        )
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Advisor agent failed: {exc}")

    return {
        "query_id": "custom",
        "original_query": request.query_text,
        "credits": request.credits,
        "suggestions_raw": advisor_result["suggestions_raw"],
        "parsed_suggestions": advisor_result["parsed_suggestions"],
        "snowflake_context_errors": sf_context.fetch_errors,
    }
```

- [ ] **Step 5: Modify the /optimize-custom route**

Replace the entire `optimize_custom_query` function with:

```python
@router.post("/optimize-custom")
async def optimize_custom_query(request: OptimizeCustomRequest):
    if request.model not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{request.model}' not supported. Choose from: {SUPPORTED_MODELS}",
        )
    if not request.selected_suggestions:
        raise HTTPException(
            status_code=400,
            detail="No suggestions selected. Please select at least one suggestion.",
        )
    if not request.query_text.strip():
        raise HTTPException(status_code=400, detail="query_text must not be empty.")

    selected_text = "\n\n".join(request.selected_suggestions)
    credits = request.credits

    try:
        creds = get_llm_credentials(request.model)
        client = LLMClient(api_key=creds["api_key"], base_url=creds["base_url"], model=request.model)
        sf_context = fetch_snowflake_context(request.query_text)
        optimizer_result = await run_optimizer_agent_async(
            client, request.query_text, selected_text, request.strategy, sf_context
        )
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Optimizer agent failed: {exc}")

    savings = optimizer_result.get("credit_savings", {})
    savings_pct = savings.get("percentage", 0.0)
    estimated_optimized_credits = round(credits * (1 - savings_pct / 100), 6)
    credits_saved = round(credits - estimated_optimized_credits, 6)

    return {
        "query_id": "custom",
        "original_query": request.query_text,
        "optimizer_result": optimizer_result,
        "cost_comparison": {
            "original_credits": credits,
            "estimated_optimized_credits": estimated_optimized_credits,
            "credits_saved": credits_saved,
            "savings_percentage": round(savings_pct, 2),
            "savings_reasoning": savings.get("reasoning", ""),
        },
        "snowflake_context_errors": sf_context.fetch_errors,
    }
```

- [ ] **Step 6: Run full test suite**

```bash
python -m pytest backend/tests/ -v
```

Expected: `28 passed` (existing) + `19 passed` (snowflake_context) — all pass.

Note: `fetch_snowflake_context` returns `SnowflakeContext(available=False)` when Snowflake is not connected (which it never is in tests). All existing route tests remain unaffected.

- [ ] **Step 7: Commit**

```bash
git add backend/api/routes.py
git commit -m "feat: wire Agent 3 into analyze/optimize routes; add snowflake_context_errors to responses (Agent 3 Task 7)"
```
