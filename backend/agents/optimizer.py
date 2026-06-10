"""Agent 2 - Query Optimizer

Input: Original SQL + optimization suggestions from Agent 1
Output: Optimized Snowflake SQL + explanation + estimated credit savings %
"""

import re
from ..llm.client import LLMClient
from ..llm.cost import calculate_cost
from ..data.admin_store import load_config
from ..models.admin_config import AdminConfig

# ------------------------------------------------------------
# Prompt
# ------------------------------------------------------------

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

# ------------------------------------------------------------
# Admin config → prompt suffix
# ------------------------------------------------------------

_GOAL_LABELS = {
    "lowest_credits": "Lowest Snowflake Credits",
    "fastest_performance": "Fastest Query Performance",
    "balanced": "Balanced Credits and Performance",
}

_AGG_LABELS = {
    "conservative": "Conservative — minimal changes, preserve existing structure",
    "moderate": "Moderate — standard optimizations",
    "aggressive": "Aggressive — maximum optimization, restructure if needed",
}


def _build_optimizer_suffix(config: AdminConfig) -> str:
    lines: list[str] = []

    r = config.optimizer_rules
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

    if enabled:
        lines.append("\nOptimization Rules:")
        lines.extend(enabled)

    lines.append(f"\nOptimization Goal: {_GOAL_LABELS.get(config.optimization_goal, config.optimization_goal)}")
    lines.append(f"Aggressiveness: {_AGG_LABELS.get(config.aggressiveness, config.aggressiveness)}")

    if config.additional_llm_instructions.strip():
        lines.append(f"\nAdditional Instructions:\n{config.additional_llm_instructions.strip()}")

    return "\n".join(lines)


# ------------------------------------------------------------
# Response parsing helpers
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Agent runners
# ------------------------------------------------------------

async def run_optimizer_agent_async(
    client: LLMClient,
    original_query: str,
    suggestions: str,
) -> dict:
    config = load_config()
    system = SYSTEM_PROMPT + _build_optimizer_suffix(config)
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
        "raw_response": content,
        "token_usage": {**cost_info, "raw_usage": raw_usage},
    }


def run_optimizer_agent(
    client: LLMClient,
    original_query: str,
    suggestions: str,
) -> dict:
    config = load_config()
    system = SYSTEM_PROMPT + _build_optimizer_suffix(config)
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
        "raw_response": content,
        "token_usage": {**cost_info, "raw_usage": raw_usage},
    }
