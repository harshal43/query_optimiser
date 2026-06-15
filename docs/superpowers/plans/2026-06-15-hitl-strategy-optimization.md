# HITL Strategy-based Optimization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `optimization_goal` with a 3-tier Strategy-based Optimization system and add a HITL pre-qualification questionnaire (Step 0) that recommends a tier before Agent 1 runs.

**Architecture:** A new `TierPreset` model holds per-tier rule bundles; `AdminConfig` gains `tier_configs: dict[str, TierPreset]` and `default_tier`. A new `POST /api/qualify` endpoint resolves a 2-answer matrix into a recommended tier. The frontend gains a persistent `HitlPanel` Step 0 component that gates the Analyze button until a tier is confirmed.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, pytest, httpx (backend); React 18, Vite (frontend). All backend tests use `fastapi.testclient.TestClient`. Run backend tests from project root with `python -m pytest backend/tests/ -v`.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `backend/models/admin_config.py` | Add TierPreset, tier_configs, default_tier; remove optimization_goal + aggressiveness |
| Modify | `backend/api/routes.py` | Add qualify endpoint + QualifyRequest/Response; add strategy param to request models |
| Modify | `backend/agents/advisor.py` | Remove _GOAL_LABELS; load rules from tier_configs[strategy]; accept strategy param |
| Modify | `backend/agents/optimizer.py` | Same as advisor.py |
| Modify | `backend/api/admin_routes.py` | No changes — Pydantic handles schema migration automatically |
| Modify | `frontend/src/services/api.js` | Add qualifyStrategy(); add strategy param to analyze/optimize functions |
| Create | `frontend/src/components/HitlPanel.jsx` | Step 0 questionnaire: 2 dropdowns, qualify call, recommendation, confirm |
| Modify | `frontend/src/App.jsx` | HITL state, canAnalyze guard, render HitlPanel, pass strategy |
| Modify | `frontend/src/components/AdminPanel.jsx` | Replace optimization_goal+aggressiveness with tier preset editor + default_tier |
| Create | `backend/tests/__init__.py` | Makes tests a package |
| Create | `backend/tests/conftest.py` | TestClient fixture |
| Create | `backend/tests/test_admin_config.py` | TierPreset model + migration tests |
| Create | `backend/tests/test_qualify.py` | qualify endpoint tests (all 9 matrix combos) |
| Create | `backend/tests/test_strategy_routing.py` | Agent strategy wiring tests |

---

## Task 1: Backend — Test Infrastructure + Update AdminConfig Schema

**Files:**
- Modify: `backend/models/admin_config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_admin_config.py`

- [ ] **Step 1: Install pytest**

```bash
cd backend
venv/Scripts/pip install pytest
```

Expected: `Successfully installed pytest-...`

- [ ] **Step 2: Create test package**

Create `backend/tests/__init__.py` (empty file).

- [ ] **Step 3: Create conftest.py**

Create `backend/tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)
```

- [ ] **Step 4: Write failing tests**

Create `backend/tests/test_admin_config.py`:

```python
import pytest
from backend.models.admin_config import AdminConfig, TierPreset, AdvisorRules, OptimizerRules, SafetyRules


def test_tier_preset_exists():
    preset = TierPreset()
    assert hasattr(preset, 'advisor_rules')
    assert hasattr(preset, 'optimizer_rules')
    assert hasattr(preset, 'safety_rules')


def test_admin_config_has_tier_configs():
    config = AdminConfig()
    assert 'conservative' in config.tier_configs
    assert 'balanced' in config.tier_configs
    assert 'aggressive' in config.tier_configs


def test_admin_config_has_default_tier():
    config = AdminConfig()
    assert config.default_tier == 'balanced'


def test_admin_config_no_optimization_goal():
    config = AdminConfig()
    assert not hasattr(config, 'optimization_goal')


def test_admin_config_no_aggressiveness():
    config = AdminConfig()
    assert not hasattr(config, 'aggressiveness')


def test_conservative_preset_is_restrictive():
    config = AdminConfig()
    conservative = config.tier_configs['conservative']
    assert conservative.advisor_rules.suggest_clustering is False
    assert conservative.optimizer_rules.simplify_nested_subqueries is False
    assert conservative.optimizer_rules.rewrite_correlated_subqueries is False
    assert conservative.safety_rules.preserve_output_order is True


def test_aggressive_preset_is_permissive():
    config = AdminConfig()
    aggressive = config.tier_configs['aggressive']
    assert aggressive.advisor_rules.suggest_avoiding_unnecessary_ctes is True
    assert aggressive.optimizer_rules.rewrite_correlated_subqueries is True
    assert aggressive.optimizer_rules.remove_redundant_order_by is True
    assert aggressive.safety_rules.preserve_output_order is False


def test_old_config_json_without_tier_configs_loads_with_defaults():
    """Pydantic must accept old admin_config.json that has no tier_configs key."""
    old_data = {
        "advisor_rules": {"detect_select_star": True},
        "optimization_goal": "lowest_credits",
        "aggressiveness": "moderate",
        "additional_llm_instructions": "",
    }
    config = AdminConfig.model_validate(old_data)
    assert 'conservative' in config.tier_configs
    assert 'balanced' in config.tier_configs
    assert 'aggressive' in config.tier_configs
```

- [ ] **Step 5: Run tests — expect ALL to fail**

```bash
python -m pytest backend/tests/test_admin_config.py -v
```

Expected: `FAILED` on all tests (TierPreset not defined yet).

- [ ] **Step 6: Implement — update `backend/models/admin_config.py`**

Replace the entire file with:

```python
from pydantic import BaseModel


class AdvisorRules(BaseModel):
    detect_select_star: bool = True
    detect_unnecessary_distinct: bool = True
    detect_cartesian_joins: bool = True
    suggest_partition_pruning: bool = True
    suggest_clustering: bool = True
    suggest_removing_redundant_order_by: bool = True
    suggest_avoiding_unnecessary_ctes: bool = False
    detect_redundant_joins: bool = True
    detect_unused_ctes: bool = True
    suggest_column_pruning: bool = True
    suggest_filter_pushdown: bool = True
    suggest_result_cache_usage: bool = True


class OptimizerRules(BaseModel):
    rewrite_union_to_union_all: bool = True
    push_predicates_earlier: bool = True
    simplify_case_expressions: bool = True
    remove_redundant_order_by: bool = False
    eliminate_unnecessary_distinct: bool = True
    simplify_nested_subqueries: bool = True
    remove_unused_columns: bool = True
    rewrite_correlated_subqueries: bool = True


class SafetyRules(BaseModel):
    preserve_query_semantics: bool = True
    preserve_output_order: bool = True


class OutputRules(BaseModel):
    generate_change_summary: bool = True


class TierPreset(BaseModel):
    advisor_rules: AdvisorRules = AdvisorRules()
    optimizer_rules: OptimizerRules = OptimizerRules()
    safety_rules: SafetyRules = SafetyRules()


def _conservative() -> TierPreset:
    return TierPreset(
        advisor_rules=AdvisorRules(
            suggest_clustering=False,
            suggest_removing_redundant_order_by=False,
            suggest_avoiding_unnecessary_ctes=False,
        ),
        optimizer_rules=OptimizerRules(
            rewrite_union_to_union_all=False,
            remove_redundant_order_by=False,
            simplify_nested_subqueries=False,
            rewrite_correlated_subqueries=False,
        ),
        safety_rules=SafetyRules(
            preserve_query_semantics=True,
            preserve_output_order=True,
        ),
    )


def _balanced() -> TierPreset:
    return TierPreset(
        advisor_rules=AdvisorRules(
            suggest_avoiding_unnecessary_ctes=False,
        ),
        optimizer_rules=OptimizerRules(
            remove_redundant_order_by=False,
            rewrite_correlated_subqueries=False,
        ),
        safety_rules=SafetyRules(
            preserve_query_semantics=True,
            preserve_output_order=True,
        ),
    )


def _aggressive() -> TierPreset:
    return TierPreset(
        advisor_rules=AdvisorRules(
            suggest_avoiding_unnecessary_ctes=True,
        ),
        optimizer_rules=OptimizerRules(
            remove_redundant_order_by=True,
            rewrite_correlated_subqueries=True,
        ),
        safety_rules=SafetyRules(
            preserve_query_semantics=True,
            preserve_output_order=False,
        ),
    )


def _default_tier_configs() -> dict:
    return {
        "conservative": _conservative(),
        "balanced": _balanced(),
        "aggressive": _aggressive(),
    }


class AdminConfig(BaseModel):
    model_config = {"extra": "ignore"}

    tier_configs: dict[str, TierPreset] = None  # type: ignore
    output_rules: OutputRules = OutputRules()
    default_tier: str = "balanced"
    additional_llm_instructions: str = ""

    def model_post_init(self, __context):
        if self.tier_configs is None:
            object.__setattr__(self, "tier_configs", _default_tier_configs())
```

- [ ] **Step 7: Run tests — expect ALL to pass**

```bash
python -m pytest backend/tests/test_admin_config.py -v
```

Expected: `8 passed`

- [ ] **Step 8: Commit**

```bash
git add backend/models/admin_config.py backend/tests/__init__.py backend/tests/conftest.py backend/tests/test_admin_config.py
git commit -m "feat: add TierPreset model and tier_configs to AdminConfig, remove optimization_goal"
```

---

## Task 2: Backend — POST /api/qualify Endpoint

**Files:**
- Modify: `backend/api/routes.py`
- Create: `backend/tests/test_qualify.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_qualify.py`:

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


@pytest.mark.parametrize("priority,tolerance,expected_tier", [
    ("cost_savings", "minimal",  "conservative"),
    ("cost_savings", "standard", "conservative"),
    ("cost_savings", "major",    "balanced"),
    ("balanced",     "minimal",  "conservative"),
    ("balanced",     "standard", "balanced"),
    ("balanced",     "major",    "aggressive"),
    ("speed",        "minimal",  "balanced"),
    ("speed",        "standard", "aggressive"),
    ("speed",        "major",    "aggressive"),
])
def test_qualify_matrix(priority, tolerance, expected_tier):
    res = client.post("/api/qualify", json={"priority": priority, "tolerance": tolerance})
    assert res.status_code == 200
    data = res.json()
    assert data["recommended_tier"] == expected_tier
    assert "rules_preview" in data


def test_qualify_rules_preview_contains_advisor_and_optimizer():
    res = client.post("/api/qualify", json={"priority": "balanced", "tolerance": "standard"})
    assert res.status_code == 200
    preview = res.json()["rules_preview"]
    assert "advisor_rules" in preview
    assert "optimizer_rules" in preview


def test_qualify_invalid_priority_returns_422():
    res = client.post("/api/qualify", json={"priority": "invalid", "tolerance": "minimal"})
    assert res.status_code == 422


def test_qualify_invalid_tolerance_returns_422():
    res = client.post("/api/qualify", json={"priority": "speed", "tolerance": "invalid"})
    assert res.status_code == 422


def test_qualify_missing_fields_returns_422():
    res = client.post("/api/qualify", json={"priority": "speed"})
    assert res.status_code == 422
```

- [ ] **Step 2: Run tests — expect ALL to fail**

```bash
python -m pytest backend/tests/test_qualify.py -v
```

Expected: `FAILED` (endpoint does not exist yet).

- [ ] **Step 3: Add qualify endpoint to `backend/api/routes.py`**

Add these request/response models right after the existing `BatchOptimizeRequest` class (around line 50):

```python
_VALID_PRIORITIES = {"cost_savings", "balanced", "speed"}
_VALID_TOLERANCES = {"minimal", "standard", "major"}

_QUALIFY_MATRIX: dict[tuple[str, str], str] = {
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


class QualifyRequest(BaseModel):
    priority: str
    tolerance: str


class QualifyResponse(BaseModel):
    recommended_tier: str
    rules_preview: dict
```

Then add the endpoint after the `/data-source` route:

```python
@router.post("/qualify", response_model=QualifyResponse)
def qualify_strategy(request: QualifyRequest):
    if request.priority not in _VALID_PRIORITIES:
        raise HTTPException(
            status_code=422,
            detail=f"priority must be one of {sorted(_VALID_PRIORITIES)}",
        )
    if request.tolerance not in _VALID_TOLERANCES:
        raise HTTPException(
            status_code=422,
            detail=f"tolerance must be one of {sorted(_VALID_TOLERANCES)}",
        )
    config = load_config()
    tier = _QUALIFY_MATRIX[(request.priority, request.tolerance)]
    preset = config.tier_configs.get(tier, config.tier_configs[config.default_tier])
    rules_preview = {
        "advisor_rules": preset.advisor_rules.model_dump(),
        "optimizer_rules": preset.optimizer_rules.model_dump(),
    }
    return QualifyResponse(recommended_tier=tier, rules_preview=rules_preview)
```

Also add `load_config` to the imports at the top of `routes.py`:

```python
from ..data.admin_store import load_config
```

- [ ] **Step 4: Run tests — expect ALL to pass**

```bash
python -m pytest backend/tests/test_qualify.py -v
```

Expected: `13 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/api/routes.py backend/tests/test_qualify.py
git commit -m "feat: add POST /api/qualify endpoint with 9-cell strategy matrix"
```

---

## Task 3: Backend — Strategy-aware Agents

**Files:**
- Modify: `backend/api/routes.py` (add `strategy` to request models)
- Modify: `backend/agents/advisor.py`
- Modify: `backend/agents/optimizer.py`
- Create: `backend/tests/test_strategy_routing.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_strategy_routing.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.agents.advisor import _build_advisor_suffix
from backend.agents.optimizer import _build_optimizer_suffix
from backend.models.admin_config import AdminConfig


def _config():
    return AdminConfig()


def test_advisor_suffix_uses_conservative_rules():
    config = _config()
    suffix = _build_advisor_suffix(config, "conservative")
    # conservative has suggest_clustering=False — must NOT appear
    assert "clustering" not in suffix
    # conservative has suggest_partition_pruning=True — must appear
    assert "partition pruning" in suffix.lower()


def test_advisor_suffix_uses_aggressive_rules():
    config = _config()
    suffix = _build_advisor_suffix(config, "aggressive")
    # aggressive has suggest_avoiding_unnecessary_ctes=True
    assert "unnecessary ctes" in suffix.lower()


def test_advisor_suffix_uses_default_tier_on_unknown_strategy():
    config = _config()
    suffix = _build_advisor_suffix(config, "nonexistent_tier")
    # should not raise — falls back to default_tier
    assert isinstance(suffix, str)


def test_optimizer_suffix_uses_conservative_rules():
    config = _config()
    suffix = _build_optimizer_suffix(config, "conservative")
    # conservative has rewrite_correlated_subqueries=False — must NOT appear
    assert "correlated" not in suffix


def test_optimizer_suffix_uses_aggressive_rules():
    config = _config()
    suffix = _build_optimizer_suffix(config, "aggressive")
    # aggressive has rewrite_correlated_subqueries=True
    assert "correlated" in suffix


def test_advisor_suffix_has_no_optimization_goal_label():
    config = _config()
    suffix = _build_advisor_suffix(config, "balanced")
    assert "Optimization Goal" not in suffix
    assert "lowest_credits" not in suffix
    assert "fastest_performance" not in suffix


def test_optimizer_suffix_has_no_optimization_goal_label():
    config = _config()
    suffix = _build_optimizer_suffix(config, "balanced")
    assert "Primary Objective" not in suffix
    assert "lowest_credits" not in suffix
```

- [ ] **Step 2: Run tests — expect ALL to fail**

```bash
python -m pytest backend/tests/test_strategy_routing.py -v
```

Expected: `FAILED` (functions don't accept strategy param yet).

- [ ] **Step 3: Update `backend/agents/advisor.py`**

Replace the entire file:

```python
"""Agent 1 - Query Optimization Advisor

Input: Raw Snowflake SQL query + strategy tier
Output: Numbered optimization suggestions (raw text + parsed list)
"""

import re
from ..llm.client import LLMClient
from ..llm.cost import calculate_cost
from ..data.admin_store import load_config
from ..models.admin_config import AdminConfig

SYSTEM_PROMPT = """You are a Snowflake SQL performance expert with deep knowledge of:
- Snowflake query optimization patterns
- Clustering keys and micro-partition pruning
- Materialized views, result caching, and warehouse sizing
- CTE vs subquery trade-offs in Snowflake's optimizer
- JOIN order and filter pushdown
- QUALIFY, WINDOW functions, and lateral joins

Analyze the provided SQL query and return ONLY structured optimization suggestions.

Format your response EXACTLY as follows:

SUGGESTIONS:
1. [Short title of suggestion]
   Explanation: [What to change and why it improves performance]
   Snowflake Note: [Any Snowflake-specific consideration, or "N/A"]

2. [Short title of suggestion]
   Explanation: [...]
   Snowflake Note: [...]

... (continue for all relevant suggestions, ordered by impact — highest first)

Do NOT include any preamble, summary, or conclusion outside this structure.
"""

_TIER_LABELS = {
    "conservative": "Conservative — minimal changes, preserve existing structure",
    "balanced":     "Balanced — standard optimizations",
    "aggressive":   "Aggressive — maximum optimization, restructure if needed",
}


def _build_advisor_suffix(config: AdminConfig, strategy: str) -> str:
    tier = strategy if strategy in config.tier_configs else config.default_tier
    r = config.tier_configs[tier].advisor_rules
    lines: list[str] = []

    enabled: list[str] = []
    if r.detect_select_star:
        enabled.append("- Detect SELECT * usage and suggest selecting only needed columns.")
    if r.detect_unnecessary_distinct:
        enabled.append("- Detect unnecessary DISTINCT clauses.")
    if r.detect_cartesian_joins:
        enabled.append("- Detect Cartesian joins (missing or inadequate JOIN conditions).")
    if r.suggest_partition_pruning:
        enabled.append("- Suggest partition pruning via WHERE on partition columns.")
    if r.suggest_clustering:
        enabled.append("- Suggest clustering key optimisations.")
    if r.suggest_removing_redundant_order_by:
        enabled.append("- Suggest removing redundant ORDER BY in subqueries or CTEs.")
    if r.suggest_avoiding_unnecessary_ctes:
        enabled.append("- Suggest avoiding unnecessary CTEs that add overhead.")
    if r.detect_redundant_joins:
        enabled.append("- Detect redundant joins that produce no additional filtering or data.")
    if r.detect_unused_ctes:
        enabled.append("- Detect CTEs that are defined but never referenced.")
    if r.suggest_column_pruning:
        enabled.append("- Suggest pruning unused columns from SELECT lists and intermediate results.")
    if r.suggest_filter_pushdown:
        enabled.append("- Suggest pushing filter conditions (WHERE/HAVING) as early as possible.")
    if r.suggest_result_cache_usage:
        enabled.append("- Suggest leveraging Snowflake result cache for repeated identical queries.")

    if enabled:
        lines.append("\nAdvisor Rules Enabled:")
        lines.extend(enabled)

    lines.append(f"\nStrategy: {_TIER_LABELS.get(tier, tier)}")

    safety = config.tier_configs[tier].safety_rules
    if safety.preserve_query_semantics:
        lines.append("Safety: Preserve exact query semantics — do not change what data is returned.")

    if config.additional_llm_instructions.strip():
        lines.append(f"\nAdditional Instructions:\n{config.additional_llm_instructions.strip()}")

    return "\n".join(lines)


def parse_suggestions(raw: str) -> list:
    text = re.sub(r'(?i)^SUGGESTIONS:\s*', '', raw.strip())
    parts = re.split(r'\n(?=\d+\.)', text)
    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(r'^(\d+)\.\s*(.*?)\n(.*)', part, re.DOTALL)
        if not m:
            continue
        result.append({
            "number": int(m.group(1)),
            "title": m.group(2).strip(),
            "body": m.group(3).strip(),
            "full_text": part.strip(),
        })
    return result


async def run_advisor_agent_async(client: LLMClient, query: str, strategy: str = "") -> dict:
    config = load_config()
    system = SYSTEM_PROMPT + _build_advisor_suffix(config, strategy)
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


def run_advisor_agent(client: LLMClient, query: str, strategy: str = "") -> dict:
    config = load_config()
    system = SYSTEM_PROMPT + _build_advisor_suffix(config, strategy)
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

- [ ] **Step 4: Update `backend/agents/optimizer.py`**

Replace the entire file:

```python
"""Agent 2 - Query Optimizer

Input: Original SQL + optimization suggestions from Agent 1 + strategy tier
Output: Optimized Snowflake SQL + explanation + estimated credit savings %
"""

import re
from ..llm.client import LLMClient
from ..llm.cost import calculate_cost
from ..data.admin_store import load_config
from ..models.admin_config import AdminConfig

SYSTEM_PROMPT = """You are a Snowflake SQL rewrite engineer.

You will receive:
1. An original Snowflake SQL query
2. A list of optimization suggestions from a performance advisor

Your job is to:
- Produce a fully optimized version of the query
- Explain every change you made
- Estimate the percentage reduction in Snowflake credits the optimized query will achieve

Respond EXACTLY in this format (do not add any text outside these sections):

OPTIMIZED_QUERY:
```sql
-- paste the complete optimized SQL here
```

EXPLANATION:
[For each change you made, write one numbered item:]
1. [Change title]: [What you changed and why — reference the suggestion it came from]
2. ...

CREDIT_SAVINGS_ESTIMATE: [A single number between 0 and 99 — the estimated percentage reduction in Snowflake credits]
Reasoning: [one concise sentence explaining why this reduction is expected]
"""

_TIER_LABELS = {
    "conservative": "Conservative — minimal changes, preserve existing structure",
    "balanced":     "Balanced — standard optimizations",
    "aggressive":   "Aggressive — maximum optimization, restructure if needed",
}


def _build_optimizer_suffix(config: AdminConfig, strategy: str) -> str:
    tier = strategy if strategy in config.tier_configs else config.default_tier
    r = config.tier_configs[tier].optimizer_rules
    lines: list[str] = []

    enabled: list[str] = []
    if r.rewrite_union_to_union_all:
        enabled.append("- Rewrite UNION to UNION ALL where duplicates are not expected.")
    if r.push_predicates_earlier:
        enabled.append("- Push predicates (WHERE conditions) earlier in the query execution.")
    if r.simplify_case_expressions:
        enabled.append("- Simplify CASE expressions where possible.")
    if r.remove_redundant_order_by:
        enabled.append("- Remove redundant ORDER BY clauses in subqueries.")
    if r.eliminate_unnecessary_distinct:
        enabled.append("- Eliminate unnecessary DISTINCT clauses.")
    if r.simplify_nested_subqueries:
        enabled.append("- Simplify nested subqueries using JOINs or CTEs.")
    if r.remove_unused_columns:
        enabled.append("- Remove unused columns from SELECT lists and intermediate CTEs.")
    if r.rewrite_correlated_subqueries:
        enabled.append("- Rewrite correlated subqueries as JOINs or window functions where possible.")

    if enabled:
        lines.append("\nOptimization Rules:")
        lines.extend(enabled)

    s = config.tier_configs[tier].safety_rules
    safety: list[str] = []
    if s.preserve_query_semantics:
        safety.append("- Preserve exact query semantics — do not change what data is returned.")
    if s.preserve_output_order:
        safety.append("- Preserve output ordering — do not remove or reorder top-level ORDER BY.")
    if safety:
        lines.append("\nSafety Constraints (must be respected):")
        lines.extend(safety)

    lines.append(f"\nStrategy: {_TIER_LABELS.get(tier, tier)}")

    if config.output_rules.generate_change_summary:
        lines.append(
            "\nAfter CREDIT_SAVINGS_ESTIMATE, append a CHANGE_SUMMARY section exactly like this:\n"
            "CHANGE_SUMMARY:\n"
            "Changes Applied:\n"
            "✓ [Each specific change made, one per line]\n\n"
            "Expected Benefits:\n"
            "- [Each expected benefit, one per line]\n\n"
            "Do not fabricate exact percentage figures in the benefits."
        )

    if config.additional_llm_instructions.strip():
        lines.append(f"\nAdditional Instructions:\n{config.additional_llm_instructions.strip()}")

    return "\n".join(lines)


def extract_sql(content: str) -> str:
    match = re.search(r'```sql\s*(.*?)\s*```', content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r'OPTIMIZED_QUERY:\s*(.*?)(?=EXPLANATION:|$)', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content.strip()


def extract_explanation(content: str) -> str:
    match = re.search(r'EXPLANATION:\s*(.*?)(?=CREDIT_SAVINGS_ESTIMATE:|$)', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r'EXPLANATION:\s*(.*)', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def extract_change_summary(content: str) -> str:
    match = re.search(r'CHANGE_SUMMARY:\s*(.*?)$', content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def extract_credit_savings(content: str) -> dict:
    pct = 0.0
    reasoning = ""
    match = re.search(r'CREDIT_SAVINGS_ESTIMATE:\s*(\d+(?:\.\d+)?)', content, re.IGNORECASE)
    if match:
        pct = min(float(match.group(1)), 95.0)
    reasoning_match = re.search(r'CREDIT_SAVINGS_ESTIMATE:.*?Reasoning:\s*(.*?)$', content, re.DOTALL | re.IGNORECASE)
    if reasoning_match:
        reasoning = reasoning_match.group(1).strip()
    return {"percentage": round(pct, 2), "reasoning": reasoning}


async def run_optimizer_agent_async(
    client: LLMClient,
    original_query: str,
    suggestions: str,
    strategy: str = "",
) -> dict:
    config = load_config()
    system = SYSTEM_PROMPT + _build_optimizer_suffix(config, strategy)
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


def run_optimizer_agent(
    client: LLMClient,
    original_query: str,
    suggestions: str,
    strategy: str = "",
) -> dict:
    config = load_config()
    system = SYSTEM_PROMPT + _build_optimizer_suffix(config, strategy)
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

- [ ] **Step 5: Add `strategy` param to request models in `backend/api/routes.py`**

Update the four request models:

```python
class AnalyzeRequest(BaseModel):
    query_id: str
    model: str
    strategy: str = ""

class OptimizeRequest(BaseModel):
    query_id: str
    model: str
    selected_suggestions: List[str]
    strategy: str = ""

class AnalyzeCustomRequest(BaseModel):
    query_text: str
    credits: float = 0.0
    model: str
    strategy: str = ""

class OptimizeCustomRequest(BaseModel):
    query_text: str
    credits: float = 0.0
    model: str
    selected_suggestions: List[str]
    strategy: str = ""
```

- [ ] **Step 6: Pass `strategy` to agent calls in `backend/api/routes.py`**

In the `analyze_query` handler, update the agent call:
```python
advisor_result = await run_advisor_agent_async(client, query_data["query_text"], request.strategy)
```

In the `optimize_query` handler:
```python
optimizer_result = await run_optimizer_agent_async(client, original_query, selected_text, request.strategy)
```

In the `analyze_custom_query` handler:
```python
advisor_result = await run_advisor_agent_async(client, request.query_text, request.strategy)
```

In the `optimize_custom_query` handler:
```python
optimizer_result = await run_optimizer_agent_async(client, request.query_text, selected_text, request.strategy)
```

Batch handlers (`analyze_one`, `optimize_one`) do NOT get strategy — they use the agent default (`"balanced"`) which falls back to `config.default_tier`.

- [ ] **Step 7: Run all backend tests**

```bash
python -m pytest backend/tests/ -v
```

Expected: all tests pass. If `test_strategy_routing.py` fails, check `_build_advisor_suffix` signature matches what tests call.

- [ ] **Step 8: Commit**

```bash
git add backend/agents/advisor.py backend/agents/optimizer.py backend/api/routes.py backend/tests/test_strategy_routing.py
git commit -m "feat: strategy-aware agents; add strategy param to analyze/optimize endpoints"
```

---

## Task 4: Frontend — Add qualifyStrategy to api.js

**Files:**
- Modify: `frontend/src/services/api.js`

- [ ] **Step 1: Add `qualifyStrategy` and update analyze/optimize functions**

In `frontend/src/services/api.js`, add after `fetchSnowflakeQueries`:

```js
export async function qualifyStrategy(priority, tolerance) {
  const res = await fetch(`${BASE}/qualify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ priority, tolerance }),
  });
  return handleResponse(res);
}
```

Update `analyzeQuery` to accept and pass strategy:

```js
export async function analyzeQuery(queryId, model, strategy = '') {
  const res = await fetch(`${BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query_id: queryId, model, strategy }),
  });
  return handleResponse(res);
}
```

Update `optimizeQuery`:

```js
export async function optimizeQuery(queryId, model, selectedSuggestions, strategy = '') {
  const res = await fetch(`${BASE}/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query_id: queryId, model, selected_suggestions: selectedSuggestions, strategy }),
  });
  return handleResponse(res);
}
```

Update `analyzeCustomQuery`:

```js
export async function analyzeCustomQuery(queryText, credits, model, strategy = '') {
  const res = await fetch(`${BASE}/analyze-custom`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query_text: queryText, credits: credits || 0, model, strategy }),
  });
  return handleResponse(res);
}
```

Update `optimizeCustomQuery`:

```js
export async function optimizeCustomQuery(queryText, credits, model, selectedSuggestions, strategy = '') {
  const res = await fetch(`${BASE}/optimize-custom`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query_text: queryText, credits: credits || 0, model, selected_suggestions: selectedSuggestions, strategy }),
  });
  return handleResponse(res);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/services/api.js
git commit -m "feat: add qualifyStrategy to api.js; add strategy param to analyze/optimize calls"
```

---

## Task 5: Frontend — Create HitlPanel Component

**Files:**
- Create: `frontend/src/components/HitlPanel.jsx`

- [ ] **Step 1: Create `frontend/src/components/HitlPanel.jsx`**

```jsx
import { useState, useEffect } from 'react';
import { qualifyStrategy } from '../services/api.js';

const PRIORITIES = [
  { value: 'cost_savings', label: 'Cost Savings — reduce Snowflake credits' },
  { value: 'balanced',     label: 'Balanced — balance cost and speed' },
  { value: 'speed',        label: 'Speed — fastest execution, cost secondary' },
];

const TOLERANCES = [
  { value: 'minimal',  label: 'Minimal — safe micro-optimizations only' },
  { value: 'standard', label: 'Standard — standard rewrites acceptable' },
  { value: 'major',    label: 'Major — full restructure permitted' },
];

const TIER_COLORS = {
  conservative: { bg: 'rgba(88,166,255,0.08)', border: 'var(--accent-dim)', text: 'var(--accent)' },
  balanced:     { bg: 'rgba(63,185,80,0.08)',  border: 'rgba(63,185,80,0.4)', text: 'var(--success)' },
  aggressive:   { bg: 'rgba(255,123,114,0.08)', border: 'rgba(255,123,114,0.4)', text: '#f85149' },
};

const TIER_LABEL = {
  conservative: 'Conservative',
  balanced:     'Balanced',
  aggressive:   'Aggressive',
};

export default function HitlPanel({ onConfirm, onReset }) {
  const [priority, setPriority]           = useState('');
  const [tolerance, setTolerance]         = useState('');
  const [qualifying, setQualifying]       = useState(false);
  const [recommended, setRecommended]     = useState(null);
  const [rulesPreview, setRulesPreview]   = useState(null);
  const [overrideTier, setOverrideTier]   = useState('');
  const [showRules, setShowRules]         = useState(false);
  const [confirmed, setConfirmed]         = useState(false);
  const [error, setError]                 = useState('');

  const effectiveTier = overrideTier || recommended;

  useEffect(() => {
    if (!priority || !tolerance) {
      setRecommended(null);
      setRulesPreview(null);
      setOverrideTier('');
      setConfirmed(false);
      onReset();
      return;
    }
    setQualifying(true);
    setError('');
    qualifyStrategy(priority, tolerance)
      .then((res) => {
        setRecommended(res.recommended_tier);
        setRulesPreview(res.rules_preview);
        setOverrideTier('');
        setConfirmed(false);
        onReset();
      })
      .catch((err) => setError(`Strategy qualification failed: ${err.message}`))
      .finally(() => setQualifying(false));
  }, [priority, tolerance]);

  const handleConfirm = () => {
    if (!effectiveTier) return;
    setConfirmed(true);
    onConfirm(effectiveTier);
  };

  const handleChange = () => {
    setConfirmed(false);
    onReset();
  };

  const colors = effectiveTier ? TIER_COLORS[effectiveTier] : null;

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="card-title" style={{ marginBottom: 14 }}>
        Strategy Questionnaire
        <span className="badge" style={{ marginLeft: 8, background: 'rgba(163,113,247,0.15)', color: '#a371f7' }}>STEP 0</span>
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
        <div className="field" style={{ flex: 1, minWidth: 220, marginBottom: 0 }}>
          <label>Business Priority</label>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            disabled={confirmed}
          >
            <option value="">Select priority...</option>
            {PRIORITIES.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>

        <div className="field" style={{ flex: 1, minWidth: 220, marginBottom: 0 }}>
          <label>Change Tolerance</label>
          <select
            value={tolerance}
            onChange={(e) => setTolerance(e.target.value)}
            disabled={confirmed}
          >
            <option value="">Select tolerance...</option>
            {TOLERANCES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
      </div>

      {qualifying && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-dim)', fontFamily: 'var(--sans)' }}>
          <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2, borderColor: 'rgba(88,166,255,0.2)', borderTopColor: 'var(--accent)' }} />
          Calculating recommended strategy...
        </div>
      )}

      {error && (
        <div style={{ fontSize: 12, color: '#f85149', fontFamily: 'var(--sans)' }}>{error}</div>
      )}

      {!qualifying && effectiveTier && (
        <div style={{
          background: colors.bg,
          border: `1px solid ${colors.border}`,
          borderRadius: 'var(--radius)',
          padding: '10px 14px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: colors.text, fontFamily: 'var(--sans)' }}>
                ✦ {confirmed ? 'Strategy:' : 'Recommended:'} {TIER_LABEL[effectiveTier]}
              </span>
              {!confirmed && recommended && (
                <div className="field" style={{ marginBottom: 0 }}>
                  <select
                    value={overrideTier}
                    onChange={(e) => setOverrideTier(e.target.value)}
                    style={{ fontSize: 11, padding: '3px 8px', height: 'auto' }}
                  >
                    <option value="">Use recommended</option>
                    <option value="conservative">Conservative</option>
                    <option value="balanced">Balanced</option>
                    <option value="aggressive">Aggressive</option>
                  </select>
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {rulesPreview && !confirmed && (
                <button
                  onClick={() => setShowRules((v) => !v)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--sans)', padding: '3px 6px' }}
                >
                  {showRules ? '▾ Hide rules' : '▸ Show rules'}
                </button>
              )}
              {!confirmed ? (
                <button
                  className="btn-optimize"
                  onClick={handleConfirm}
                  style={{ fontSize: 12, padding: '5px 14px', minWidth: 'unset' }}
                >
                  ✓ Confirm
                </button>
              ) : (
                <button
                  onClick={handleChange}
                  style={{ background: 'none', border: '1px solid var(--border-2)', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--sans)', padding: '4px 10px' }}
                >
                  Change
                </button>
              )}
            </div>
          </div>

          {showRules && !confirmed && rulesPreview && (
            <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
              {Object.entries(rulesPreview.advisor_rules ?? {})
                .filter(([, v]) => v)
                .map(([k]) => (
                  <span key={k} style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'var(--sans)' }}>
                    ✓ {k.replace(/_/g, ' ')}
                  </span>
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/HitlPanel.jsx
git commit -m "feat: add HitlPanel Step 0 questionnaire component"
```

---

## Task 6: Frontend — Update App.jsx

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add HITL state and import**

At the top of `App.jsx`, add the import:

```js
import HitlPanel from './components/HitlPanel.jsx';
```

After the existing state declarations (around line 46), add:

```js
const [confirmedTier, setConfirmedTier] = useState(null);
```

- [ ] **Step 2: Update `canAnalyze` guard**

Find the existing `canAnalyze` line (around line 312):

```js
const canAnalyze = !!config.model && !analyzing && !optimizing && inputMode !== 'snowflake'
  && (inputMode !== 'excel' || !!selectedQueryId);
```

Replace with:

```js
const canAnalyze = !!config.model && !analyzing && !optimizing && inputMode !== 'snowflake'
  && (inputMode !== 'excel' || !!selectedQueryId)
  && !!confirmedTier;
```

- [ ] **Step 3: Update `handleAnalyze` to pass strategy**

Find the `handleAnalyze` callback. Update the two `analyzeQuery` / `analyzeCustomQuery` calls:

```js
if (inputMode === 'custom') {
  res = await analyzeCustomQuery(customQueryText, parseFloat(customCredits) || 0, config.model, confirmedTier);
} else {
  res = await analyzeQuery(selectedQueryId, config.model, confirmedTier);
}
```

- [ ] **Step 4: Update `handleOptimize` to pass strategy**

Find the `handleOptimize` callback. Update the two `optimizeQuery` / `optimizeCustomQuery` calls:

```js
if (inputMode === 'custom') {
  res = await optimizeCustomQuery(customQueryText, parseFloat(customCredits) || 0, config.model, selectedTexts, confirmedTier);
} else {
  res = await optimizeQuery(selectedQueryId, config.model, selectedTexts, confirmedTier);
}
```

- [ ] **Step 5: Render HitlPanel above ConfigPanel**

Find the `<ConfigPanel ... />` JSX (around line 361). Add `<HitlPanel>` directly above it:

```jsx
<HitlPanel
  onConfirm={(tier) => setConfirmedTier(tier)}
  onReset={() => setConfirmedTier(null)}
/>

<ConfigPanel
  ...existing props...
/>
```

- [ ] **Step 6: Update Analyze button tooltip / label in ConfigPanel (if it shows strategy)**

Open `frontend/src/components/ConfigPanel.jsx`. Find the Analyze button. Add the confirmed tier badge to its label if you want visual confirmation. This step is optional — skip if ConfigPanel just uses `canAnalyze` to disable the button and the HitlPanel itself shows the confirmed state clearly.

- [ ] **Step 7: Verify in browser**

Start both servers:

```bash
# Terminal 1 — backend
cd backend && uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

Check:
1. HitlPanel appears above query selector
2. Both dropdowns empty → Analyze button disabled
3. Fill both dropdowns → recommendation appears
4. Click Confirm → Analyze button enabled, shows confirmed state
5. Click Change → Analyze button disabled again
6. Confirm then click Analyze → request includes `strategy` field (check browser Network tab)

- [ ] **Step 8: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: wire HitlPanel into App; gate canAnalyze on confirmedTier; pass strategy to API calls"
```

---

## Task 7: Frontend — Update AdminPanel

**Files:**
- Modify: `frontend/src/components/AdminPanel.jsx`

- [ ] **Step 1: Update `DEFAULT_CONFIG` constant**

Replace the existing `DEFAULT_CONFIG` object (which has `optimization_goal` and `aggressiveness`) with:

```js
const TIERS = ['conservative', 'balanced', 'aggressive'];

const DEFAULT_TIER_PRESET = {
  advisor_rules: {
    detect_select_star: true,
    detect_unnecessary_distinct: true,
    detect_cartesian_joins: true,
    detect_redundant_joins: true,
    detect_unused_ctes: true,
    suggest_partition_pruning: true,
    suggest_clustering: true,
    suggest_column_pruning: true,
    suggest_filter_pushdown: true,
    suggest_result_cache_usage: true,
    suggest_removing_redundant_order_by: true,
    suggest_avoiding_unnecessary_ctes: false,
  },
  optimizer_rules: {
    rewrite_union_to_union_all: true,
    push_predicates_earlier: true,
    simplify_case_expressions: true,
    remove_redundant_order_by: false,
    eliminate_unnecessary_distinct: true,
    simplify_nested_subqueries: true,
    remove_unused_columns: true,
    rewrite_correlated_subqueries: true,
  },
  safety_rules: {
    preserve_query_semantics: true,
    preserve_output_order: true,
  },
};

const DEFAULT_CONFIG = {
  tier_configs: {
    conservative: {
      advisor_rules: { ...DEFAULT_TIER_PRESET.advisor_rules, suggest_clustering: false, suggest_removing_redundant_order_by: false, suggest_avoiding_unnecessary_ctes: false },
      optimizer_rules: { ...DEFAULT_TIER_PRESET.optimizer_rules, rewrite_union_to_union_all: false, simplify_nested_subqueries: false, rewrite_correlated_subqueries: false },
      safety_rules: { preserve_query_semantics: true, preserve_output_order: true },
    },
    balanced: {
      advisor_rules: { ...DEFAULT_TIER_PRESET.advisor_rules, suggest_avoiding_unnecessary_ctes: false },
      optimizer_rules: { ...DEFAULT_TIER_PRESET.optimizer_rules, remove_redundant_order_by: false, rewrite_correlated_subqueries: false },
      safety_rules: { preserve_query_semantics: true, preserve_output_order: true },
    },
    aggressive: {
      advisor_rules: { ...DEFAULT_TIER_PRESET.advisor_rules, suggest_avoiding_unnecessary_ctes: true },
      optimizer_rules: { ...DEFAULT_TIER_PRESET.optimizer_rules, remove_redundant_order_by: true, rewrite_correlated_subqueries: true },
      safety_rules: { preserve_query_semantics: true, preserve_output_order: false },
    },
  },
  output_rules: { generate_change_summary: true },
  default_tier: 'balanced',
  additional_llm_instructions: '',
};
```

- [ ] **Step 2: Update state setters**

Replace `setAdvisorRule`, `setOptimizerRule`, `setSafetyRule` with tier-aware versions. Remove `setTop` calls for `optimization_goal` and `aggressiveness`. Add tier rule setter:

```js
const setTierRule = useCallback((tier, ruleGroup, key, val) => {
  setConfig((p) => ({
    ...p,
    tier_configs: {
      ...p.tier_configs,
      [tier]: {
        ...p.tier_configs[tier],
        [ruleGroup]: {
          ...p.tier_configs[tier][ruleGroup],
          [key]: val,
        },
      },
    },
  }));
}, []);

const setTop = useCallback((key, val) => setConfig((p) => ({ ...p, [key]: val })), []);
```

- [ ] **Step 3: Replace the "Shared Settings" card in the JSX**

Find the existing Shared Settings card (the one with `optimization_goal` and `aggressiveness` dropdowns) and replace with:

```jsx
<div className="card">
  <div className="card-title" style={{ marginBottom: 16 }}>Strategy-based Optimization</div>
  <div style={{ marginBottom: 20 }}>
    <div className="field" style={{ maxWidth: 280, marginBottom: 0 }}>
      <label>Default Tier (used for Batch)</label>
      <select value={config.default_tier} onChange={(e) => setTop('default_tier', e.target.value)}>
        <option value="conservative">Conservative</option>
        <option value="balanced">Balanced</option>
        <option value="aggressive">Aggressive</option>
      </select>
    </div>
  </div>

  {TIERS.map((tier) => (
    <TierSection
      key={tier}
      tier={tier}
      preset={config.tier_configs?.[tier] ?? DEFAULT_CONFIG.tier_configs[tier]}
      onChange={(ruleGroup, key, val) => setTierRule(tier, ruleGroup, key, val)}
    />
  ))}
</div>
```

- [ ] **Step 4: Add `TierSection` component at bottom of file**

```jsx
function TierSection({ tier, preset, onChange }) {
  const [open, setOpen] = useState(false);
  const tierLabel = { conservative: 'Conservative', balanced: 'Balanced', aggressive: 'Aggressive' }[tier];
  const tierColor = { conservative: 'var(--accent)', balanced: 'var(--success)', aggressive: '#f85149' }[tier];

  return (
    <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12, marginTop: 12 }}>
      <div
        onClick={() => setOpen((v) => !v)}
        style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', userSelect: 'none', marginBottom: open ? 12 : 0 }}
      >
        <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>{open ? '▾' : '▸'}</span>
        <span style={{ fontWeight: 600, fontSize: 13, color: tierColor, fontFamily: 'var(--sans)' }}>{tierLabel}</span>
      </div>
      {open && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <RuleCard
            title="Advisor Rules"
            badge={{ label: 'AGENT 1', style: {} }}
            rules={ADVISOR_RULES}
            values={preset.advisor_rules}
            onChange={(key, val) => onChange('advisor_rules', key, val)}
          />
          <RuleCard
            title="Optimizer Rules"
            badge={{ label: 'AGENT 2', style: { background: 'rgba(63,185,80,0.15)', color: 'var(--success)' } }}
            rules={OPTIMIZER_RULES}
            values={preset.optimizer_rules}
            onChange={(key, val) => onChange('optimizer_rules', key, val)}
          />
          <RuleCard
            title="Safety Rules"
            badge={{ label: 'GUARDRAILS', style: { background: 'rgba(255,166,0,0.15)', color: '#f0a500' } }}
            rules={SAFETY_RULES}
            values={preset.safety_rules}
            onChange={(key, val) => onChange('safety_rules', key, val)}
          />
        </div>
      )}
    </div>
  );
}
```

Add `import { useState, useEffect, useCallback } from 'react';` already covers `useState` — no extra import needed for `TierSection`.

- [ ] **Step 5: Remove the old four `<RuleCard>` blocks**

Delete the four top-level `<RuleCard>` JSX blocks for "Advisor Agent Rules", "Optimizer Agent Rules", "Safety Rules", and "Output Rules" from the `AdminPanel` return. They are now inside `TierSection`. Keep only the Output Rules card as a separate top-level card (it applies globally, not per-tier):

```jsx
<RuleCard
  title="Output Rules"
  badge={{ label: 'OUTPUT', style: { background: 'rgba(163,113,247,0.15)', color: '#a371f7' } }}
  rules={OUTPUT_RULES}
  values={config.output_rules}
  onChange={setOutputRule}
  hint="Controls what additional content the optimizer agent includes in its response."
/>
```

Keep `setOutputRule` callback as is.

- [ ] **Step 6: Update `handleReset` to use new DEFAULT_CONFIG**

The existing `handleReset` sets `config` back to `DEFAULT_CONFIG`. Since `DEFAULT_CONFIG` is now updated, this works without changes.

- [ ] **Step 7: Verify admin panel in browser**

1. Open Admin panel (⚙ Admin button)
2. Verify: no "Optimization Goal" dropdown, no "Aggressiveness" dropdown
3. Verify: "Strategy-based Optimization" section with "Default Tier" dropdown + 3 collapsible tier sections
4. Expand "Balanced" tier → check rule toggles appear
5. Toggle a rule → save config → reload → verify persisted

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/AdminPanel.jsx
git commit -m "feat: replace optimization_goal/aggressiveness with per-tier preset editor in AdminPanel"
```

---

## Task 8: Run Full Test Suite + Final Verification

- [ ] **Step 1: Run all backend tests**

```bash
python -m pytest backend/tests/ -v
```

Expected output (all pass):
```
test_admin_config.py::test_tier_preset_exists PASSED
test_admin_config.py::test_admin_config_has_tier_configs PASSED
test_admin_config.py::test_admin_config_has_default_tier PASSED
test_admin_config.py::test_admin_config_no_optimization_goal PASSED
test_admin_config.py::test_admin_config_no_aggressiveness PASSED
test_admin_config.py::test_conservative_preset_is_restrictive PASSED
test_admin_config.py::test_aggressive_preset_is_permissive PASSED
test_admin_config.py::test_old_config_json_without_tier_configs_loads_with_defaults PASSED
test_qualify.py::test_qualify_matrix[cost_savings-minimal-conservative] PASSED
... (all 9 matrix combos)
test_qualify.py::test_qualify_rules_preview_contains_advisor_and_optimizer PASSED
test_qualify.py::test_qualify_invalid_priority_returns_422 PASSED
test_qualify.py::test_qualify_invalid_tolerance_returns_422 PASSED
test_qualify.py::test_qualify_missing_fields_returns_422 PASSED
test_strategy_routing.py::... PASSED
```

- [ ] **Step 2: Delete stale `admin_config.json` if it exists**

The old file has `optimization_goal` and `aggressiveness` keys. Pydantic ignores unknown fields on load, but it's cleaner to delete so the first admin save writes a fresh schema:

```bash
rm -f backend/admin_config.json
```

(Pydantic defaults will initialize tier_configs on next load.)

- [ ] **Step 3: End-to-end browser test**

1. Start backend: `uvicorn backend.main:app --reload --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:5173
4. Verify HitlPanel appears at top (Step 0)
5. Select "Cost Savings" + "Minimal" → recommendation: **Conservative** → Confirm
6. Select a query → Click Analyze → succeeds
7. Open Network tab → confirm request body contains `"strategy": "conservative"`
8. Complete optimization flow → succeeds
9. Open Admin (⚙) → verify tier preset editor, no optimization_goal dropdown
10. Change "Default Tier" to "aggressive" → Save → reload → verify persisted

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete HITL strategy-based optimization system"
```
