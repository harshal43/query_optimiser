# HITL Strategy-based Optimization — Design Spec
**Date:** 2026-06-15  
**Status:** Approved  
**Scope:** Query Optimizer Admin Panel re-architecture + Human-in-the-Loop pre-qualification questionnaire

---

## 1. Overview

### Problem
The current `AdminConfig` uses an `optimization_goal` classification ("Lowest Credits / Fastest Performance / Balanced") that is being deprecated. The `aggressiveness` field (conservative / moderate / aggressive) is being repurposed as the primary strategy classification, publicly renamed **Strategy-based Optimization**.

### Solution
1. Replace `optimization_goal` with a 3-tier **Strategy-based Optimization** system: **Conservative**, **Balanced**, **Aggressive**.
2. Add a **Human-in-the-Loop (HITL) pre-qualification questionnaire** (Step 0) that dynamically recommends a tier before Agent 1 runs.
3. Admin panel gains per-tier rule preset editor with per-rule overrides.

---

## 2. HITL Questionnaire

### Questions

**Question 1 — Business Priority**
> "What is your primary optimization goal?"

| Value | Label |
|---|---|
| `cost_savings` | Cost Savings — reduce Snowflake credits |
| `balanced` | Balanced — balance cost and speed |
| `speed` | Speed — fastest execution, cost secondary |

**Question 2 — Change Tolerance**
> "How much can the query structure change?"

| Value | Label |
|---|---|
| `minimal` | Minimal — safe micro-optimizations only |
| `standard` | Standard — standard rewrites (CTEs, predicate pushdown, etc.) |
| `major` | Major — full restructure permitted |

### Tier Recommendation Matrix

| Priority \ Tolerance | minimal | standard | major |
|---|---|---|---|
| `cost_savings` | conservative | conservative | balanced |
| `balanced` | conservative | balanced | aggressive |
| `speed` | balanced | aggressive | aggressive |

### UX Flow
1. User fills both dropdowns in the **Step 0 HITL Panel** (persistent, above query selector)
2. Frontend calls `POST /api/qualify` with `{priority, tolerance}`
3. Panel shows recommended tier + collapsible rules preview
4. User clicks **Confirm** (or manually overrides tier) → `confirmed_tier` stored in React state
5. Analyze button enabled only after tier confirmed
6. `confirmed_tier` passed to `/api/analyze` and `/api/optimize`

### Batch Processing
Batch endpoints (`/api/batch-analyze`, `/api/batch-optimize`) bypass HITL. They use `AdminConfig.default_tier` (admin-configured).

---

## 3. Backend Changes

### 3a. Schema (`backend/models/admin_config.py`)

**Remove:** `optimization_goal: str` field entirely.

**Add:** `TierPreset` model and `tier_configs` dict on `AdminConfig`:

```python
class TierPreset(BaseModel):
    advisor_rules: AdvisorRules = AdvisorRules()
    optimizer_rules: OptimizerRules = OptimizerRules()
    safety_rules: SafetyRules = SafetyRules()

class AdminConfig(BaseModel):
    tier_configs: dict[str, TierPreset] = {
        "conservative": TierPreset(...),
        "balanced":     TierPreset(...),
        "aggressive":   TierPreset(...),
    }
    output_rules: OutputRules = OutputRules()
    default_tier: str = "balanced"
    additional_llm_instructions: str = ""
```

`aggressiveness` field removed — replaced by `default_tier`.

### 3b. Default Rule Presets

| Rule | Conservative | Balanced | Aggressive |
|---|---|---|---|
| detect_select_star | ✓ | ✓ | ✓ |
| detect_unnecessary_distinct | ✓ | ✓ | ✓ |
| detect_cartesian_joins | ✓ | ✓ | ✓ |
| suggest_partition_pruning | ✓ | ✓ | ✓ |
| suggest_clustering | ✗ | ✓ | ✓ |
| detect_redundant_joins | ✓ | ✓ | ✓ |
| detect_unused_ctes | ✓ | ✓ | ✓ |
| suggest_column_pruning | ✓ | ✓ | ✓ |
| suggest_filter_pushdown | ✓ | ✓ | ✓ |
| suggest_result_cache_usage | ✓ | ✓ | ✓ |
| suggest_removing_redundant_order_by | ✗ | ✓ | ✓ |
| suggest_avoiding_unnecessary_ctes | ✗ | ✗ | ✓ |
| rewrite_union_to_union_all | ✗ | ✓ | ✓ |
| push_predicates_earlier | ✓ | ✓ | ✓ |
| simplify_case_expressions | ✓ | ✓ | ✓ |
| eliminate_unnecessary_distinct | ✓ | ✓ | ✓ |
| simplify_nested_subqueries | ✗ | ✓ | ✓ |
| remove_unused_columns | ✓ | ✓ | ✓ |
| rewrite_correlated_subqueries | ✗ | ✗ | ✓ |
| remove_redundant_order_by | ✗ | ✗ | ✓ |
| preserve_query_semantics | ✓ | ✓ | ✓ |
| preserve_output_order | ✓ | ✓ | ✗ |

### 3c. New Endpoint: `POST /api/qualify`

**Request:**
```python
class QualifyRequest(BaseModel):
    priority: str   # "cost_savings" | "balanced" | "speed"
    tolerance: str  # "minimal" | "standard" | "major"
```

**Response:**
```python
class QualifyResponse(BaseModel):
    recommended_tier: str
    rules_preview: dict  # active rules for that tier
```

**Matrix lookup (Python dict, no DB):**
```python
_MATRIX = {
    ("cost_savings", "minimal"):  "conservative",
    ("cost_savings", "standard"): "conservative",
    ("cost_savings", "major"):    "balanced",
    ("balanced",     "minimal"):  "conservative",
    ("balanced",     "standard"): "balanced",
    ("balanced",     "major"):    "aggressive",
    ("speed",        "minimal"):  "balanced",
    ("speed",        "standard"): "aggressive",
    ("speed",        "major"):    "aggressive",
}
```

Invalid `priority`/`tolerance` values → 422 Unprocessable Entity.

### 3d. Request Model Changes

Add `strategy: str = "balanced"` to:
- `AnalyzeRequest`
- `OptimizeRequest`
- `AnalyzeCustomRequest`
- `OptimizeCustomRequest`

`BatchAnalyzeRequest` and `BatchOptimizeRequest` — **unchanged**.

### 3e. Agent Changes (`advisor.py`, `optimizer.py`)

- Remove `_GOAL_LABELS` dict and all `optimization_goal` references
- `run_advisor_agent_async` + `run_optimizer_agent_async` accept new `strategy: str` param
- Rule loading changes from flat config to tier config:

```python
# before
r = config.advisor_rules

# after
r = config.tier_configs[strategy].advisor_rules
```

- Prompt suffix labels updated: tier name replaces aggressiveness label (e.g. `"Strategy: Conservative — minimal changes, preserve existing structure"`)
- Fallback: if `strategy` not found in `tier_configs`, use `config.default_tier`

---

## 4. Frontend Changes

### 4a. New Component: `HitlPanel`

**File:** `frontend/src/components/HitlPanel.jsx`

Layout:
```
┌─ Strategy Questionnaire ──────────────────────────────────┐
│  Business Priority    [Cost Savings ▾]                     │
│  Change Tolerance     [Minimal      ▾]                     │
│                                                            │
│  ✦ Recommended: Conservative                               │
│    [▸ Show active rules]          [Change ▾] [Confirm ✓]  │
└────────────────────────────────────────────────────────────┘
```

Behavior:
- Both dropdowns empty on load → Analyze button disabled
- Both filled → auto-calls `POST /api/qualify` → shows recommendation + rules preview
- **Confirm** → `confirmedTier` set in React state → Analyze enabled
- **Change** → resets `confirmedTier` to null → Analyze disabled
- User may override recommended tier before confirming
- Confirmed tier shown as badge on Analyze button: `Analyze [Conservative]`

### 4b. State Changes (`main.jsx`)

```js
const [hitlAnswers, setHitlAnswers]     = useState({ priority: '', tolerance: '' })
const [recommendedTier, setRecommendedTier] = useState(null)
const [confirmedTier, setConfirmedTier] = useState(null)
const [rulesPreview, setRulesPreview]   = useState(null)

const canAnalyze = !!selectedQueryId && !!confirmedTier
```

### 4c. Analyze / Optimize Call Changes

```js
// analyze
{ query_id, model, strategy: confirmedTier }

// optimize
{ query_id, model, selected_suggestions, strategy: confirmedTier }

// custom analyze
{ query_text, credits, model, strategy: confirmedTier }

// custom optimize
{ query_text, credits, model, selected_suggestions, strategy: confirmedTier }
```

Batch calls unchanged — no `strategy` field.

### 4d. Unchanged Components

`SuggestionsPanel`, `CostBreakdown`, `CostComparison`, `SqlDisplay`, `BatchPanel`, `SnowflakeConnectModal`, `TokenBadge`, `OriginalQueryPanel` — no changes.

---

## 5. Admin Panel Changes

### 5a. Removed
- `optimization_goal` dropdown ("Lowest Credits / Fastest Performance / Balanced") — deleted
- Flat `aggressiveness` dropdown — replaced by `default_tier` selector

### 5b. New Tier Preset Editor

3 collapsible sections — one per tier. Each section exposes all Advisor, Optimizer, and Safety rule toggles for that tier independently.

```
┌─ Strategy-based Optimization ─────────────────────────────┐
│  Default Tier (for Batch):  [Balanced ▾]                  │
│                                                            │
│  ▸ Conservative                                            │
│  ▾ Balanced                                                │
│    Advisor Rules                                           │
│      ☑ Detect SELECT *          ☑ Detect unused CTEs      │
│      ☑ Detect cartesian joins   ☑ Suggest filter pushdown │
│      ...                                                   │
│    Optimizer Rules                                         │
│      ☑ Rewrite UNION → UNION ALL                          │
│      ☑ Push predicates earlier                            │
│      ...                                                   │
│    Safety Rules                                            │
│      ☑ Preserve query semantics                           │
│      ☑ Preserve output order                              │
│  ▸ Aggressive                                              │
└────────────────────────────────────────────────────────────┘
```

Saved via existing `POST /api/admin/config` — no new admin endpoints needed.

---

## 6. Error Handling

### Frontend
| Scenario | Behavior |
|---|---|
| User skips Step 0 | Analyze disabled. Tooltip: "Complete Strategy Questionnaire first." |
| `/api/qualify` fails | Inline error in panel. Tier not confirmed. User can retry. |
| User changes answers after confirming | `confirmedTier` reset to null → Analyze disabled |
| User overrides recommended tier | Accepted silently — no warning |

### Backend
| Scenario | Behavior |
|---|---|
| `strategy` not in `tier_configs` | Fall back to `config.default_tier`. Log warning. |
| Invalid `priority`/`tolerance` in `/api/qualify` | 422 Unprocessable Entity |
| Old `admin_config.json` (no `tier_configs`) | Pydantic defaults auto-initialize 3 tiers |
| Old `admin_config.json` has `optimization_goal` key | Pydantic ignores unknown fields — no error |

---

## 7. Migration

- **Zero manual migration.** Old `admin_config.json` missing `tier_configs` → Pydantic defaults on `load_config()`. First admin save writes new schema.
- `optimization_goal` in old JSON → silently ignored by Pydantic.

---

## 8. Testing

| Layer | Test |
|---|---|
| Backend unit | All 9 matrix combinations return correct tier |
| Backend unit | `TierPreset` defaults serialize/deserialize correctly |
| Backend unit | Old `admin_config.json` (no `tier_configs`) loads without error |
| API integration | `POST /api/qualify` correct for all 9 input combinations |
| API integration | `POST /api/analyze` with `strategy="conservative"` loads conservative rules |
| API integration | `POST /api/batch-analyze` ignores `strategy`, uses `default_tier` |
| Frontend | `HitlPanel` keeps Analyze disabled until tier confirmed |
| Frontend | Changing answers after confirm resets `confirmedTier` |
| Frontend | Manual tier override accepted and passed to analyze call |
