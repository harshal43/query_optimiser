# HITL Pre-Qualification Questionnaire

Before Agent 1 (Optimization Advisor) runs, the user answers 2 questions. Their answers determine which **Strategy-based Optimization** tier is recommended.

---

## Question 1 — Business Priority

> **"What is your primary optimization goal?"**

| Option | Meaning |
|---|---|
| **Cost Savings** | Reduce Snowflake credits consumed |
| **Balanced** | Balance cost reduction and query speed |
| **Speed** | Fastest possible query execution, cost secondary |

---

## Question 2 — Change Tolerance

> **"How much can the query structure change?"**

| Option | Meaning |
|---|---|
| **Minimal** | Preserve existing structure — safe micro-optimizations only |
| **Standard** | Standard rewrites acceptable (CTEs, predicate pushdown, column pruning, etc.) |
| **Major** | Full restructure OK — maximum optimization even if query looks significantly different |

---

## Tier Recommendation Matrix

Answers feed a lookup table that recommends one of three **Strategy-based Optimization** tiers:

| Business Priority \ Change Tolerance | Minimal | Standard | Major |
|---|---|---|---|
| **Cost Savings** | Conservative | Conservative | Balanced |
| **Balanced** | Conservative | Balanced | Aggressive |
| **Speed** | Balanced | Aggressive | Aggressive |

---

## Tiers

| Tier | Public Name | Behavior |
|---|---|---|
| **Conservative** | Conservative Optimization | Minimal changes, preserve structure, low risk |
| **Balanced** | Balanced Optimization | Standard rewrites, moderate restructuring |
| **Aggressive** | Aggressive Optimization | Maximum optimization, full restructure permitted |

---

## Flow

1. User fills both dropdowns in the Step 0 HITL panel
2. System calls `POST /api/qualify` with `{priority, tolerance}`
3. Backend returns `{recommended_tier, rules_preview}`
4. Panel displays recommendation — e.g. *"Recommended: Conservative"*
5. User accepts or manually overrides the tier
6. Confirmed tier is passed to Agent 1 (`/api/analyze`) and Agent 2 (`/api/optimize`)
