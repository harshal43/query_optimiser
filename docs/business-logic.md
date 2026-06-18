# Query Optimiser — Business Logic

## 1. Problem Statement

Snowflake SQL queries written by analysts and engineers are often inefficient — they scan more data than needed, use expensive patterns like correlated subqueries or cartesian joins, and miss platform-specific features like clustering key pruning and result caching. Each inefficiency directly translates to higher Snowflake credit consumption and slower query execution.

Manually reviewing and rewriting queries at scale is time-consuming and requires deep Snowflake expertise. The Query Optimiser solves this by automating the analysis and rewriting process using LLMs, guided by live schema context from the connected Snowflake account and configurable optimization rules.

---

## 2. System Overview

The Query Optimiser is a full-stack web application:

- **Frontend**: React 18 SPA — query selection, analysis, optimization, HITL interactions, and result display
- **Backend**: FastAPI (Python) — multi-agent LLM pipeline, Snowflake connectivity, rule configuration
- **LLM Support**: Claude (Anthropic) and GPT-4o (OpenAI) — pluggable per-request
- **Data Source**: Uploaded Excel/CSV files or live Snowflake query history

---

## 3. Core User Journey

```
1. Connect to Snowflake (optional but enables richer context)
2. Load queries (upload Excel/CSV or fetch from Snowflake)
3. Select a query → Qualify optimization strategy
4. Analyze → Review suggestions → Resolve HITL flags
5. Optimize → Review optimized SQL + explanation
6. Run on Snowflake → Compare KPIs (before vs after)
```

---

## 4. The Four-Agent Pipeline

The system uses four specialised agents in sequence. Each agent has a single responsibility.

### Agent 1 — Advisor

**Input**: Original SQL query + strategy tier  
**Output**: Numbered optimization suggestions + HITL flags

The Advisor analyses the SQL and produces a structured list of performance improvement opportunities, ordered by estimated impact. It operates using a configurable rulebook — which patterns to detect, and which to ignore — based on the active strategy tier.

**Patterns the Advisor detects:**
- `SELECT *` usage — cannot prune micro-partitions without known column list
- Missing `WHERE` filter on large tables — no partition pruning possible
- Cartesian joins — tables joined without an explicit key
- `ORDER BY` without `LIMIT` — may be unintentional
- Non-sargable predicates — e.g., `YEAR(created_at) = 2024` prevents index use
- Unnecessary `DISTINCT`, redundant `ORDER BY` in subqueries
- Unused or redundant CTEs, redundant joins
- Opportunities for clustering key exploitation and result cache reuse

**HITL Flags**: When the Advisor encounters a pattern it cannot resolve without human input (e.g., `SELECT *` — which columns are actually needed?), it emits a Human-in-the-Loop flag. These flags are surfaced to the user before optimization runs so the user can provide the missing context.

---

### Agent 2 — Optimizer

**Input**: Original SQL + selected suggestions from Agent 1 + resolved HITL flags + strategy tier + live Snowflake schema  
**Output**: Rewritten SQL + explanation of each change + estimated credit savings %

The Optimizer rewrites the query according to the selected suggestions and a configurable rewriting rulebook. Key behaviours:

- Only applies the suggestions the user selected — no unsolicited changes
- Operates under a **strict schema constraint**: all column and table names in the output must match the live Snowflake schema fetched by Agent 3. The LLM is explicitly instructed never to invent column names.
- Produces a numbered explanation tied to each suggestion applied
- Estimates percentage reduction in Snowflake credit consumption
- Optionally generates a `CHANGE_SUMMARY` section (configurable)

**Schema violation detection**: After the LLM produces the rewritten SQL, the system parses it with `sqlglot` and compares every column reference against the live schema. Any column not found in the schema (and not an alias defined within the query) is flagged as a schema violation and shown as a warning in the UI.

---

### Agent 3 — Snowflake Context Fetcher

**Input**: Original SQL  
**Output**: Per-table metadata — columns, data types, nullability, constraints, clustering key, row count

Agent 3 runs before both Agent 1 and Agent 2. It parses the SQL to extract referenced table names, then queries `INFORMATION_SCHEMA` to fetch live schema data for each table. This data is injected into the system prompts of both agents.

**What it fetches per table:**
- Column names, data types, nullable flags
- PK / UNIQUE / FK constraints (where role has access)
- Clustering key and clustering depth (micro-partition scan efficiency indicator)
- Row count

**Resilience:**
- Results are TTL-cached (5 minutes) to avoid redundant Snowflake calls
- Cache is invalidated automatically when the connected database/schema changes
- If `INFORMATION_SCHEMA` access is restricted for some views, the affected sub-query is skipped and processing continues with whatever data was retrievable
- If Snowflake is not connected, agents receive no schema context and operate on SQL text alone

---

### Agent 4 — Query Runner

**Input**: Original SQL + Optimized SQL + active Snowflake connection  
**Output**: KPI comparison — execution time, bytes scanned, partitions scanned, spill, credits

Agent 4 executes both queries on Snowflake and compares the real execution metrics. For the original query, it first searches `INFORMATION_SCHEMA.QUERY_HISTORY` for a recent successful run to avoid redundant execution. The optimized query is always executed fresh to get accurate post-optimization numbers.

**KPIs captured:**
| Metric | What it measures |
|---|---|
| `elapsed_ms` | Total wall-clock execution time |
| `bytes_scanned` | Data volume read from storage |
| `bytes_spilled_local` | Memory overflow to local SSD |
| `bytes_spilled_remote` | Memory overflow to remote storage |
| `partitions_scanned` | Micro-partitions touched |
| `partitions_total` | Total micro-partitions in table |
| `rows_produced` | Result set size |
| `credits` | Snowflake compute credits consumed |

**Safety**: Only `SELECT` statements (including CTEs) are accepted. A `LIMIT 100` guard is automatically added to all queries before execution to prevent full table scans during comparison. Write statements are rejected.

---

## 5. Strategy Tier System

Before optimization, the user optionally qualifies their intent using two dimensions:

| Dimension | Options |
|---|---|
| **Priority** | Cost savings / Balanced / Speed |
| **Tolerance** | Minimal change / Standard / Major restructure |

These map to one of three optimization tiers:

| Tier | Character |
|---|---|
| **Conservative** | Minimal changes — safe rewrites only, structure preserved |
| **Balanced** | Standard optimizations — moderate rewrites |
| **Aggressive** | Maximum optimization — restructure if needed, ORDER BY may be removed |

Each tier has its own **Advisor rulebook** (which patterns to detect) and **Optimizer rulebook** (which rewrites to apply), both configurable by an admin. The user can also override the recommended tier manually in the UI.

**Qualification matrix** (priority × tolerance → tier):

|  | Minimal | Standard | Major |
|---|---|---|---|
| Cost savings | Conservative | Conservative | Balanced |
| Balanced | Conservative | Balanced | Aggressive |
| Speed | Balanced | Aggressive | Aggressive |

---

## 6. Human-in-the-Loop (HITL) Workflow

When Agent 1 detects patterns it cannot resolve without domain knowledge, it emits HITL flags. The UI surfaces these flags as interactive inputs before the user triggers optimization.

**Example HITL flag types:**
- `select_star` — which columns are actually needed?
- `missing_filter` — what filter should be applied to this large table?
- `non_sargable` — what is the exact date range for this year-based filter?
- `cartesian_join` — what is the intended join key between these tables?
- `order_by_no_limit` — is the ORDER BY intentional without a LIMIT?

The user provides answers (or skips). The resolved answers are prepended to the suggestions block given to the Optimizer, so the rewritten SQL incorporates the user's domain knowledge.

---

## 7. Admin Configuration

An admin panel exposes full control over system behaviour without code changes:

- **Per-tier rulebook**: toggle individual advisor and optimizer rules on/off for each tier
- **Default tier**: which tier applies when no qualification is done
- **Safety rules**: enforce semantic equivalence, preserve output ordering
- **Output rules**: enable/disable change summary generation
- **Additional LLM instructions**: free-text instructions appended to every agent's system prompt (e.g., "Always use Snowflake-native QUALIFY instead of subqueries")

Configuration is persisted to a JSON file on the server and loaded on every request.

---

## 8. Batch Processing

For high-volume workloads, the system supports batch analysis and optimization:

- Upload an Excel/CSV file with multiple queries
- Select all or a subset of queries
- Run batch analyze (parallel, capped at 5 concurrent LLM calls)
- Review per-query suggestions and select optimizations
- Run batch optimize
- Export all results to Excel

---

## 9. Cost Tracking

Every LLM call records token usage (prompt + completion) and maps it to USD cost based on per-model pricing. This is surfaced alongside each result so users can see the LLM spend for each optimization session.

Additionally, the system estimates Snowflake credit savings based on the Optimizer's `CREDIT_SAVINGS_ESTIMATE` — an LLM-generated percentage reduction — applied against the query's known credit baseline from the input data.

---

## 10. Rules Matrix

### Advisor Rules (what patterns Agent 1 detects)

| Rule | Conservative | Balanced | Aggressive |
|---|:---:|:---:|:---:|
| Detect `SELECT *` | ✓ | ✓ | ✓ |
| Detect unnecessary `DISTINCT` | ✓ | ✓ | ✓ |
| Detect cartesian joins | ✓ | ✓ | ✓ |
| Suggest partition pruning | ✓ | ✓ | ✓ |
| Suggest clustering key optimisations | — | ✓ | ✓ |
| Suggest removing redundant `ORDER BY` | — | ✓ | ✓ |
| Suggest avoiding unnecessary CTEs | — | — | ✓ |
| Detect redundant joins | ✓ | ✓ | ✓ |
| Detect unused CTEs | ✓ | ✓ | ✓ |
| Suggest column pruning | ✓ | ✓ | ✓ |
| Suggest filter pushdown | ✓ | ✓ | ✓ |
| Suggest result cache usage | ✓ | ✓ | ✓ |

### Optimizer Rules (what rewrites Agent 2 applies)

| Rule | Conservative | Balanced | Aggressive |
|---|:---:|:---:|:---:|
| Rewrite `UNION` → `UNION ALL` | — | ✓ | ✓ |
| Push predicates earlier | ✓ | ✓ | ✓ |
| Simplify `CASE` expressions | ✓ | ✓ | ✓ |
| Remove redundant `ORDER BY` in subqueries | — | — | ✓ |
| Eliminate unnecessary `DISTINCT` | ✓ | ✓ | ✓ |
| Simplify nested subqueries (→ JOINs / CTEs) | — | ✓ | ✓ |
| Remove unused columns | ✓ | ✓ | ✓ |
| Rewrite correlated subqueries (→ JOINs / window fns) | — | — | ✓ |

### Safety Rules (constraints Agent 2 must respect)

| Rule | Conservative | Balanced | Aggressive |
|---|:---:|:---:|:---:|
| Preserve exact query semantics | ✓ | ✓ | ✓ |
| Preserve output ordering | ✓ | ✓ | — |

> **Legend**: ✓ = enabled by default &nbsp;|&nbsp; — = disabled by default &nbsp;|&nbsp; All rules are individually toggleable per tier via the Admin panel.

---

## 11. Data Flow Summary

```
User Input (SQL query)
        │
        ▼
[Agent 3 — Snowflake Context]
  Fetch live schema metadata
  (columns, clustering, row counts)
        │
        ├──────────────────────────┐
        ▼                          ▼
[Agent 1 — Advisor]          Schema injected as
  Detect anti-patterns        strict constraint
  Emit suggestions
  Emit HITL flags
        │
        ▼
[User — HITL Resolution]
  Review flags
  Provide domain context
  Select suggestions
  Confirm/override tier
        │
        ▼
[Agent 2 — Optimizer]
  Rewrite SQL using suggestions
  Constrained to live schema
  Post-rewrite: schema violation check
        │
        ├─── Optimized SQL ──────────────────────┐
        │                                        ▼
        │                              [Agent 4 — Query Runner]
        │                                Execute original + optimized
        │                                Fetch KPIs from QUERY_HISTORY
        │                                Compute improvement %
        ▼                                        │
    UI Display                                   ▼
  - Optimized SQL                         KPI Comparison Panel
  - Explanation                         (time / bytes / credits delta)
  - Credit savings estimate
  - Schema violation warnings
```

---

## 11. Key Technical Guardrails

| Guardrail | Mechanism |
|---|---|
| LLM hallucination prevention | Live schema injected as strict constraint into optimizer prompt |
| Post-generation validation | sqlglot parses output SQL; unknown columns surfaced as warnings |
| Sandbox safety | Agent 4 only accepts SELECT (including CTEs); LIMIT 100 auto-injected |
| Snowflake session context | `USE DATABASE` + `USE SCHEMA` issued before every query to prevent error 090105 |
| Async safety | All synchronous Snowflake I/O offloaded via `asyncio.to_thread()` |
| Schema cache freshness | TTL 5 min; invalidated on database/schema change |
| Null strategy coercion | Frontend coerces null tier to empty string before API call to prevent 422 errors |
