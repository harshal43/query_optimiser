# Sandbox Execution & KPI Comparison Design

## Overview

Three connected features that close the loop between LLM-generated SQL rewrites and real Snowflake execution data:

1. **HITL Ambiguity Flags** — Agent 1 detects SQL patterns it cannot resolve without human input (`SELECT *`, missing partition filters, implicit joins) and emits structured `human_flags[]` alongside suggestions. Frontend renders them as editable inputs before the user triggers optimization.

2. **Query Runner (Agent 4)** — After the user confirms the optimized SQL, a new backend agent executes both the original and optimized queries on Snowflake and captures their `query_id` values.

3. **KPI Comparison** — Agent 3 gains two new functions: one to look up the original query's most recent run in `INFORMATION_SCHEMA.QUERY_HISTORY` (no lag, no credits), one to fetch structured KPIs by `query_id`. The frontend renders a side-by-side comparison table showing pre/post metrics and % improvement.

**Key constraint:** All existing behavior (analyze → optimize flow without Snowflake connected) is unchanged. Every new feature degrades gracefully when Snowflake is not connected.

---

## Architecture

```
SQL query
    │
    ▼
┌─────────────────────────────────────────┐
│  Agent 1 (advisor.py) — EXTENDED        │
│  Output: suggestions[] + human_flags[]  │
└────────────────┬────────────────────────┘
                 │ user resolves flags in UI
                 ▼
┌─────────────────────────────────────────┐
│  Agent 2 (optimizer.py) — EXTENDED      │
│  Input: suggestions + resolved_flags    │
│  Output: optimized_sql                  │
└────────────────┬────────────────────────┘
                 │ user clicks "Run on Snowflake"
                 ▼
┌─────────────────────────────────────────┐
│  POST /api/execute-comparison           │
│  ├─ Agent 3: find pre-run KPIs         │
│  │  (INFORMATION_SCHEMA history lookup) │
│  ├─ Agent 4: execute optimized_sql     │
│  │  (LIMIT 100 + capture query_id)      │
│  └─ Agent 3: fetch post-run KPIs       │
│     (by query_id)                       │
└────────────────┬────────────────────────┘
                 │
                 ▼
         ComparisonPanel (new)
         pre/post KPI table
```

---

## Data Models

### Backend (Python dataclasses)

```python
# backend/agents/advisor.py — new addition to return dict

@dataclass
class HumanFlag:
    id: str           # "hf_1", "hf_2" — stable within a response
    type: str         # see HumanFlagType below
    title: str        # short label shown above the input
    description: str  # why this matters for optimization
    placeholder: str  # instructional text inside the input field
    sql_snippet: str  # the offending SQL fragment (for context)

# HumanFlagType values:
#   "select_star"         — SELECT * with no column list
#   "missing_filter"      — no predicate on clustering-key column
#   "implicit_join"       — comma-separated FROM without explicit JOIN/ON
#   "order_without_limit" — ORDER BY on large table without LIMIT
#   "non_sargable"        — function wrapping an indexed/clustering column
```

```python
# backend/agents/query_runner.py — new file

@dataclass
class QueryKPIs:
    query_id: str
    elapsed_ms: Optional[int]
    bytes_scanned: Optional[int]
    bytes_spilled_local: Optional[int]
    bytes_spilled_remote: Optional[int]
    partitions_scanned: Optional[int]
    partitions_total: Optional[int]
    rows_produced: Optional[int]
    credits: Optional[float]
    source: str   # "history" | "live"  (live = freshly executed)
    error: Optional[str] = None

@dataclass
class ComparisonResult:
    pre: QueryKPIs
    post: QueryKPIs
    improvement: dict   # metric_name → pct_change (negative = improvement)
```

### Frontend (JS objects)

```js
// HumanFlag (from analyze response)
{ id, type, title, description, placeholder, sql_snippet }

// ResolvedFlag (user input, sent with optimize request)
{ id, value }   // value = user-typed string

// ComparisonResult (from execute-comparison)
{
  pre:  { query_id, elapsed_ms, bytes_scanned, bytes_spilled_local,
          bytes_spilled_remote, partitions_scanned, partitions_total,
          rows_produced, credits, source, error },
  post: { ...same shape },
  improvement: {
    elapsed_ms: -92.9,
    bytes_scanned: -95.3,
    partitions_scanned: -93.3,
    credits: -92.8
  }
}
```

---

## Feature 1: HITL Ambiguity Flags

### Agent 1 prompt change

Append to the existing `SYSTEM_PROMPT` in `advisor.py`:

```
After the SUGGESTIONS section, append a HUMAN_FLAGS section if any unresolvable ambiguities exist.
Format exactly:

HUMAN_FLAGS:
HF_ID: hf_1
HF_TYPE: select_star
HF_TITLE: SELECT * detected — column list needed
HF_DESCRIPTION: Cannot prune micro-partitions without knowing which columns are required.
HF_PLACEHOLDER: Enter comma-separated columns (e.g. ORDER_ID, STATUS, CREATED_AT)
HF_SNIPPET: SELECT * FROM orders

HF_ID: hf_2
...

If no ambiguities exist, omit the HUMAN_FLAGS section entirely.

Detect these patterns only:
- SELECT * without explicit column list
- No WHERE predicate on a column that appears to be a date/time partition key (when table has >1M rows context is provided)
- Comma-separated tables in FROM clause without JOIN...ON (implicit cross-join)
- ORDER BY at the outermost query without accompanying LIMIT
- Function call wrapping a column in a WHERE predicate (e.g. YEAR(col)=2024, UPPER(col)='X')
```

### Parsing

Add `parse_human_flags(raw: str) -> list[dict]` in `advisor.py`. Parse the `HUMAN_FLAGS:` block by splitting on `HF_ID:` prefixes. Return empty list if section absent. Each flag dict maps directly to `HumanFlag` fields.

### API contract change (analyze endpoints)

`/api/analyze` and `/api/analyze-custom` responses gain:
```json
"human_flags": [
  {
    "id": "hf_1",
    "type": "select_star",
    "title": "SELECT * detected — column list needed",
    "description": "Cannot prune micro-partitions without knowing which columns are required.",
    "placeholder": "Enter comma-separated columns (e.g. ORDER_ID, STATUS, CREATED_AT)",
    "sql_snippet": "SELECT * FROM orders"
  }
]
```

Empty array `[]` when no flags. Never `null`.

### API contract change (optimize endpoints)

`/api/optimize` and `/api/optimize-custom` request body gains:
```json
"resolved_flags": [
  { "id": "hf_1", "value": "ORDER_ID, CUSTOMER_ID, STATUS, CREATED_AT" }
]
```

Omitting `resolved_flags` or passing `[]` is valid — Agent 2 proceeds without resolved values (user chose to skip).

### Agent 2 prompt injection

When `resolved_flags` is non-empty, inject before the suggestions block:

```
Human-Validated Inputs (apply these when rewriting):
- hf_1 (SELECT * replacement): ORDER_ID, CUSTOMER_ID, STATUS, CREATED_AT
```

---

## Feature 2: Agent 3 KPI Extensions

### New functions in `backend/agents/snowflake_context.py`

```python
def find_recent_query_run(conn, sql_text: str) -> Optional[str]:
    """
    Search INFORMATION_SCHEMA.QUERY_HISTORY for the most recent successful
    run of sql_text. Matches on a normalized SQL fingerprint (first 500 chars,
    collapsed whitespace). Returns query_id or None.
    No lag — uses INFORMATION_SCHEMA, not ACCOUNT_USAGE.
    """
    # Normalize: strip + collapse whitespace, take first 500 chars
    # Search: SELECT QUERY_ID FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY(
    #           RESULT_LIMIT => 200,
    #           END_TIME_RANGE_START => DATEADD('days', -7, CURRENT_TIMESTAMP())
    #         ))
    #         WHERE UPPER(QUERY_TEXT) LIKE UPPER('%<fingerprint>%')
    #           AND EXECUTION_STATUS = 'SUCCESS'
    #         ORDER BY START_TIME DESC
    #         LIMIT 1

def fetch_query_kpis(conn, query_id: str) -> QueryKPIs:
    """
    Fetch performance metrics for a specific query_id.
    Uses TABLE(INFORMATION_SCHEMA.QUERY_HISTORY()) filtered by QUERY_ID.
    Returns QueryKPIs with source='history' or source='live'.
    Returns QueryKPIs with error set if query_id not found.
    """
    # SELECT QUERY_ID, TOTAL_ELAPSED_TIME, BYTES_SCANNED,
    #   BYTES_SPILLED_TO_LOCAL_STORAGE, BYTES_SPILLED_TO_REMOTE_STORAGE,
    #   PARTITIONS_SCANNED, PARTITIONS_TOTAL, ROWS_PRODUCED,
    #   CREDITS_USED_CLOUD_SERVICES
    # FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY(RESULT_LIMIT => 200))
    # WHERE QUERY_ID = '<query_id>'
```

`QueryKPIs` dataclass lives in `query_runner.py` (imported by both Agent 3 and Agent 4 functions). Agent 3 does not execute queries — only reads history.

---

## Feature 3: Agent 4 — Query Runner

### New file: `backend/agents/query_runner.py`

```python
from .snowflake_context import fetch_query_kpis, find_recent_query_run, QueryKPIs, ComparisonResult

def execute_and_capture(conn, sql: str, limit: int = 100) -> str:
    """
    Appends LIMIT {limit} to sql (if not already present), executes it,
    returns the Snowflake query_id for the completed execution.
    Raises on execution error.
    """

def _add_limit(sql: str, limit: int) -> str:
    """
    Adds LIMIT clause if the outermost SELECT does not already have one.
    Uses sqlglot to detect existing LIMIT. Never mutates CTEs or subqueries.
    """

def build_comparison(conn, original_sql: str, optimized_sql: str) -> ComparisonResult:
    """
    1. find_recent_query_run(conn, original_sql)
       → if found: pre_id = that query_id, fetch KPIs with source='history'
       → if not found: execute_and_capture(original_sql) → pre_id,
                       fetch KPIs with source='live'
    2. execute_and_capture(conn, optimized_sql) → post_id
    3. fetch_query_kpis(conn, post_id) with source='live'
    4. compute improvement % for each metric
    5. return ComparisonResult
    """

def _compute_improvement(pre: QueryKPIs, post: QueryKPIs) -> dict:
    """
    For each numeric KPI: (post - pre) / pre * 100.
    Skips metrics where pre is None or 0.
    """
```

**Limit injection rule:** `_add_limit` appends `LIMIT 100` to the outermost query. If the SQL already has a `LIMIT` clause (detected by sqlglot), it is left unchanged. This prevents runaway full-table scans during sandbox testing while still producing real execution stats.

**No DDL guard:** `execute_and_capture` raises `ValueError` if sqlglot parses the SQL as anything other than a `SELECT` statement. Prevents accidental DML/DDL execution.

---

## Feature 4: New Route

### `POST /api/execute-comparison`

**Request body:**
```json
{
  "original_query": "SELECT * FROM orders WHERE ...",
  "optimized_query": "SELECT order_id, status FROM orders WHERE ..."
}
```

**Response (success):**
```json
{
  "pre": {
    "query_id": "01b2c3d4-...",
    "elapsed_ms": 45200,
    "bytes_scanned": 8589934592,
    "bytes_spilled_local": 0,
    "bytes_spilled_remote": 0,
    "partitions_scanned": 1200,
    "partitions_total": 1400,
    "rows_produced": 1240000,
    "credits": 0.042,
    "source": "history",
    "error": null
  },
  "post": {
    "query_id": "01b2c3d5-...",
    "elapsed_ms": 3200,
    "bytes_scanned": 398458880,
    "bytes_spilled_local": 0,
    "bytes_spilled_remote": 0,
    "partitions_scanned": 80,
    "partitions_total": 1400,
    "rows_produced": 1240000,
    "credits": 0.003,
    "source": "live",
    "error": null
  },
  "improvement": {
    "elapsed_ms": -92.9,
    "bytes_scanned": -95.4,
    "partitions_scanned": -93.3,
    "credits": -92.8
  }
}
```

**Response (Snowflake not connected):** HTTP 503 `"Not connected to Snowflake"`

**Response (execution error):** HTTP 502 with detail. `pre` may be populated even when `post` fails — the response carries partial data in this case via a non-2xx with a body containing whatever was fetched.

**Route location:** `backend/api/routes.py` — alongside existing Snowflake routes.

---

## Feature 5: Frontend Changes

### 5a. HitlFlagsPanel.jsx (new component)

Renders after Agent 1 result, only when `human_flags.length > 0`.

```
┌─────────────────────────────────────────────────────┐
│ ⚑ Human Input Required                  STEP 0.5   │
├─────────────────────────────────────────────────────┤
│ SELECT * detected — column list needed              │
│ Cannot prune micro-partitions without knowing...    │
│ ┌─────────────────────────────────────────────┐    │
│ │ Enter comma-separated columns (e.g. ORDER…) │    │
│ └─────────────────────────────────────────────┘    │
│                                                     │
│ No partition filter on ORDERS                       │
│ ORDERS has clustering key on CREATED_AT...          │
│ ┌─────────────────────────────────────────────┐    │
│ │ Enter date range predicate (e.g. CREATED_AT…│    │
│ └─────────────────────────────────────────────┘    │
│                                                     │
│              [Skip flags]  [Apply & Optimize →]     │
└─────────────────────────────────────────────────────┘
```

Props: `flags: HumanFlag[]`, `onConfirm(resolvedFlags: ResolvedFlag[])`, `onSkip()`.

State: `values: { [id]: string }` — controlled inputs, one per flag.

"Apply & Optimize" calls `onConfirm` with all non-empty values as `ResolvedFlag[]`. "Skip flags" calls `onSkip()` — proceeds with `resolved_flags = []`.

### 5b. ComparisonPanel.jsx (new component)

Renders after `execute-comparison` response. Only shown when Snowflake is connected and comparison result is available.

```
┌─────────────────────────────────────────────────────────┐
│ Snowflake Execution Comparison          [▶ Re-run]       │
├──────────────────────┬──────────────────┬───────────────┤
│                      │ BEFORE           │ AFTER         │
├──────────────────────┼──────────────────┼───────────────┤
│ Elapsed time         │ 45,200 ms        │ 3,200 ms      │  -92.9% ✓
│ Bytes scanned        │ 8.0 GB           │ 380 MB        │  -95.4% ✓
│ Partitions scanned   │ 1,200 / 1,400    │ 80 / 1,400    │  -93.3% ✓
│ Rows produced        │ 1,240,000        │ 1,240,000     │  0%
│ Credits used         │ 0.042            │ 0.003         │  -92.8% ✓
│ Spill (local)        │ 0 B              │ 0 B           │  —
├──────────────────────┴──────────────────┴───────────────┤
│ Source: BEFORE = from history · AFTER = live execution  │
└─────────────────────────────────────────────────────────┘
```

Improvement % shown in green for negative values (less = better for all metrics except rows_produced which should be unchanged).

Null metric = "—". Source annotation at bottom distinguishes history vs live.

### 5c. OptimizedQueryPanel.jsx — "Run on Snowflake" button

Add below the existing Regenerate/Correct buttons, only when `snowflakeConnected && optimizerResult`:

```jsx
<button
  className="btn btn-primary"
  onClick={onRunComparison}
  disabled={running}
>
  ▶ Run on Snowflake
</button>
```

### 5d. App.jsx state additions

```js
const [humanFlags, setHumanFlags]           = useState([]);
const [comparisonResult, setComparisonResult] = useState(null);
const [comparisonLoading, setComparisonLoading] = useState(false);
```

`handleAnalyze` sets `humanFlags` from the analyze response. `handleRunComparison` calls `POST /api/execute-comparison`, sets `comparisonResult`.

### 5e. api.js additions

```js
export async function executeComparison(originalQuery, optimizedQuery) { ... }
```

---

## Graceful Degradation

| State | Behavior |
|---|---|
| Snowflake not connected | `human_flags` still returned (LLM-only). "Run on Snowflake" button hidden. ComparisonPanel never shown. |
| No human flags detected | `human_flags: []`. HitlFlagsPanel not rendered. User goes straight to optimize. |
| User skips flags | `resolved_flags: []` sent. Agent 2 gets no extra context. |
| Original query not in history | Agent 4 executes it fresh with LIMIT 100. `pre.source = "live"`. |
| Optimized query execution fails | HTTP 502. Frontend shows error state in ComparisonPanel. Pre data shown if available. |
| KPI field not returned by Snowflake | Field is `null`. UI shows "—". Improvement % skipped for that metric. |

---

## Files

### New
- `backend/models/kpi_models.py` — `QueryKPIs`, `ComparisonResult` dataclasses (shared between Agent 3 and Agent 4 to avoid circular import)
- `backend/agents/query_runner.py` — `execute_and_capture`, `build_comparison`, `_add_limit`, `_compute_improvement`
- `backend/tests/test_query_runner.py` — tests for query runner
- `frontend/src/components/HitlFlagsPanel.jsx` — flag inputs UI
- `frontend/src/components/ComparisonPanel.jsx` — KPI comparison table

### Modified
- `backend/agents/advisor.py` — add `HUMAN_FLAGS` to system prompt, add `parse_human_flags`, extend return dict
- `backend/agents/snowflake_context.py` — add `find_recent_query_run`, `fetch_query_kpis`, import `QueryKPIs` from `backend.models.kpi_models`
- `backend/api/routes.py` — add `POST /api/execute-comparison`, extend analyze/optimize request/response models, inject resolved_flags into suggestions string before passing to Agent 2
- `backend/tests/test_snowflake_context.py` — add tests for two new functions
- `frontend/src/App.jsx` — add `humanFlags`, `comparisonResult` state, wire handlers
- `frontend/src/components/OptimizedQueryPanel.jsx` — add "Run on Snowflake" button
- `frontend/src/services/api.js` — add `executeComparison`

### Not modified
- `backend/data/snowflake_connector.py` — Agent 3/4 read `_conn` from here, no changes
- `backend/agents/optimizer.py` — no signature change; `resolved_flags` merged into the `suggestions` string by routes.py before the call

---

## Tests

### `test_query_runner.py`

```python
# All Snowflake calls mocked via MagicMock cursor

test_add_limit_appends_when_absent()         # SELECT * FROM t → SELECT * FROM t LIMIT 100
test_add_limit_preserves_existing()          # SELECT * FROM t LIMIT 5 → unchanged
test_add_limit_does_not_touch_subquery()     # outer LIMIT only
test_execute_and_capture_returns_query_id()  # mock cursor, verify query_id extracted
test_execute_and_capture_rejects_non_select()  # INSERT INTO → ValueError
test_compute_improvement_basic()             # 100 → 10: -90.0%
test_compute_improvement_skips_null_pre()    # pre=None → metric absent from result
test_compute_improvement_skips_zero_pre()    # pre=0 → no division by zero
test_build_comparison_uses_history_when_found()   # find_recent_query_run returns id → pre.source='history'
test_build_comparison_executes_when_not_in_history()  # find_recent_query_run returns None → pre.source='live'
```

### `test_snowflake_context.py` additions

```python
test_find_recent_query_run_returns_id_when_found()
test_find_recent_query_run_returns_none_when_absent()
test_fetch_query_kpis_populates_all_fields()
test_fetch_query_kpis_handles_null_fields()
```

### `test_advisor.py` additions (or in existing test file)

```python
test_parse_human_flags_extracts_all_fields()
test_parse_human_flags_returns_empty_when_no_section()
test_parse_human_flags_handles_multiple_flags()
```

---

## Dependencies

No new Python packages. `sqlglot` (already installed) used in `_add_limit` for SELECT detection and LIMIT clause check.

---

## Circular import note

`snowflake_context.py` needs `QueryKPIs` (return type of `fetch_query_kpis`). `query_runner.py` calls `find_recent_query_run` and `fetch_query_kpis` from `snowflake_context.py`. If both files define or import from each other, a circular dependency results.

**Resolution:** `QueryKPIs` and `ComparisonResult` live in `backend/models/kpi_models.py`. Both `snowflake_context.py` and `query_runner.py` import from there. No circular dependency.

## resolved_flags injection path

`optimizer.py` signature stays unchanged (`suggestions: str` param). Routes.py constructs the suggestions string passed to Agent 2 as:

```python
flags_block = ""
if resolved_flags:
    lines = ["Human-Validated Inputs (apply these when rewriting):"]
    for f in resolved_flags:
        lines.append(f"- {f['id']}: {f['value']}")
    flags_block = "\n".join(lines) + "\n\n"

selected_text = flags_block + "\n\n".join(request.selected_suggestions)
```

This keeps Agent 2's interface simple — it receives one string and rewrites accordingly.

---

## Scope boundary

**In scope:**
- HITL flags for 5 pattern types (SELECT *, missing filter, implicit join, ORDER without LIMIT, non-SARGable)
- Sandbox execution with LIMIT 100 guard, SELECT-only guard
- KPI fetch via INFORMATION_SCHEMA (no ACCOUNT_USAGE)
- Side-by-side comparison table
- Graceful degradation at every failure point

**Out of scope:**
- Storing comparison history across sessions
- EXPLAIN plan comparison (no execution plan AST diff)
- Batch comparison across multiple queries
- Automatic flag resolution (user must always fill inputs manually)
- Retry logic for flaky Snowflake connections
