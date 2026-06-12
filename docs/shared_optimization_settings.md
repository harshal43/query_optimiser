# Shared Optimization Settings

## What It Is

Two dropdowns in the Admin Configuration panel that control how both LLM agents reason about query optimization.

- **Optimization Goal** — *what* to optimize for
- **Optimization Aggressiveness** — *how boldly* to optimize

They are orthogonal axes, not redundant. Together they form a 3×3 behavioral matrix.

---

## How It Works Internally

```
Admin Panel (UI)
      |
      v
POST /admin/config  →  admin_config.json  (persisted on disk)
      |
      v
Every agent call: load_config() reads fresh from disk
      |
      +--> Advisor Agent (Agent 1)  →  _build_advisor_suffix(config)
      |
      +--> Optimizer Agent (Agent 2) →  _build_optimizer_suffix(config)
```

Settings are appended as plain text to each agent's system prompt at runtime. No code branches on them — the LLM reads the instructions and self-governs its output.

### Advisor prompt suffix (advisor.py)
```
Optimization Goal: Lowest Snowflake Credits
Aggressiveness: Moderate — standard optimizations
```

### Optimizer prompt suffix (optimizer.py)
```
Primary Objective: Lowest Snowflake Credits
Aggressiveness: Moderate — standard optimizations
```

---

## Optimization Goal

| Value | Label | LLM Behavior |
|---|---|---|
| `lowest_credits` | Lowest Credits | Prioritize credit-reducing rewrites — partition pruning, DISTINCT removal, column pruning |
| `fastest_performance` | Fastest Performance | Prioritize latency — better JOIN order, parallel scans, avoid spill to disk |
| `balanced` | Balanced | Weigh credits and performance equally |

---

## Optimization Aggressiveness

| Value | Label | LLM Behavior |
|---|---|---|
| `conservative` | Conservative | Minimal changes — only high-confidence, low-risk rewrites |
| `moderate` | Moderate | Standard set of rewrites — default behavior |
| `aggressive` | Aggressive | Major restructuring allowed — JOIN rewrites, CTE splits, subquery rewrites |

---

## Combined Behavior Matrix

| Goal | Aggressiveness | Result |
|---|---|---|
| `lowest_credits` | `conservative` | Cut credits, safe changes only |
| `lowest_credits` | `moderate` | Cut credits, standard rewrites |
| `lowest_credits` | `aggressive` | Cut credits at any cost — restructure everything |
| `fastest_performance` | `conservative` | Prefer speed, don't touch JOIN order |
| `fastest_performance` | `moderate` | Speed-focused standard rewrites |
| `fastest_performance` | `aggressive` | Rewrite JOINs, subqueries, CTEs — whatever makes it fastest |
| `balanced` | `conservative` | Gentle, balanced suggestions |
| `balanced` | `moderate` | Default behavior |
| `balanced` | `aggressive` | Bold rewrites balancing both dimensions |

---

## Current Limitation

Both agents currently receive only **query text**. Settings are prompt instructions with no runtime grounding — the LLM reasons from SQL syntax alone, not actual execution behavior.

---

## Snowflake Inputs Needed for Full Effectiveness

To make Goal + Aggressiveness truly meaningful, the LLM needs runtime execution context alongside the query text.

### For `lowest_credits` goal

| Column | Source Table | Why It Helps |
|---|---|---|
| `CREDITS_USED_CLOUD_SERVICES` | `QUERY_HISTORY` | LLM knows actual credit cost per query |
| `BYTES_SCANNED` | `QUERY_HISTORY` | Identifies expensive full-table scans |
| `PARTITIONS_SCANNED` | `QUERY_HISTORY` | Shows if partition pruning is failing |
| `PARTITIONS_TOTAL` | `QUERY_HISTORY` | Context for pruning ratio |
| `WAREHOUSE_SIZE` | `QUERY_HISTORY` | Credit burn rate depends on warehouse size |

### For `fastest_performance` goal

| Column | Source Table | Why It Helps |
|---|---|---|
| `EXECUTION_TIME` | `QUERY_HISTORY` | Actual latency to target |
| `QUEUED_OVERLOAD_TIME` | `QUERY_HISTORY` | Reveals warehouse sizing vs query structure issues |
| `COMPILATION_TIME` | `QUERY_HISTORY` | High value = complex query structure problem |
| `BYTES_SPILLED_TO_LOCAL_STORAGE` | `QUERY_HISTORY` | Critical — LLM should suggest memory-friendly rewrites |

### For `aggressive` aggressiveness

| Input | How to Get It | Why It Helps |
|---|---|---|
| Clustering keys | `SYSTEM$CLUSTERING_INFORMATION()` | LLM suggests real partition columns |
| Table row counts | `INFORMATION_SCHEMA.TABLE_STORAGE_METRICS` | LLM knows if JOIN is on 1B-row table |
| Column cardinality | `APPROX_COUNT_DISTINCT` | Tells if DISTINCT is actually needed |
| Result cache hit rate | `IS_CLIENT_GENERATED_STATEMENT` | LLM suggests cache-friendly rewrites |

### Minimum Viable Set (highest ROI, all in QUERY_HISTORY)

```sql
BYTES_SCANNED,
PARTITIONS_SCANNED,
PARTITIONS_TOTAL,
EXECUTION_TIME,
BYTES_SPILLED_TO_LOCAL_STORAGE,
CREDITS_USED_CLOUD_SERVICES
```

All already available in `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` — the same table currently queried. Adding these columns to the SQL and injecting them into the agent prompt would ground the LLM's reasoning in real execution data instead of syntax alone.
