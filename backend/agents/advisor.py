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
