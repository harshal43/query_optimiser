"""Agent 2 - Query Optimizer

Input: Original SQL + optimization suggestions from Agent 1 + strategy tier
Output: Optimized Snowflake SQL + explanation + estimated credit savings %
"""

import logging
import re

from ..llm.client import LLMClient
from ..llm.cost import calculate_cost
from ..data.admin_store import load_config
from ..models.admin_config import AdminConfig
from .snowflake_context import SnowflakeContext, build_context_block

logger = logging.getLogger(__name__)

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
    if tier not in config.tier_configs:
        tier = next(iter(config.tier_configs))
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


def _log_agent_call(sf_context: SnowflakeContext | None, strategy: str, system: str) -> None:
    ctx_summary = (
        f"available | tables={list(sf_context.tables.keys())}"
        if sf_context and sf_context.available
        else "unavailable"
    )
    logger.info("── Agent2/Optimizer START | strategy=%r | sf_context=%s", strategy or "default", ctx_summary)
    logger.debug("── SYSTEM PROMPT ──\n%s\n── END SYSTEM PROMPT ──", system)


def _log_agent_done(content: str, usage: dict) -> None:
    logger.debug("── LLM RESPONSE ──\n%s\n── END LLM RESPONSE ──", content)
    logger.info(
        "── Agent2/Optimizer DONE | prompt_tokens=%s | completion_tokens=%s",
        usage.get("prompt_tokens"), usage.get("completion_tokens"),
    )


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
    _log_agent_call(sf_context, strategy, system)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Original Snowflake SQL query:\n```sql\n{original_query}\n```\n\nOptimization suggestions:\n{suggestions}\n\nProduce the optimized query, explain all changes, and estimate credit savings."}
    ]
    response = await client.async_chat(messages, temperature=0.1)
    content = client.extract_content(response)
    usage = client.extract_usage(response)
    _log_agent_done(content, usage)
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
    sf_context: SnowflakeContext | None = None,
) -> dict:
    config = load_config()
    system = SYSTEM_PROMPT + _build_optimizer_suffix(config, strategy)
    if sf_context is not None:
        system += build_context_block(sf_context)
    _log_agent_call(sf_context, strategy, system)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Original Snowflake SQL query:\n```sql\n{original_query}\n```\n\nOptimization suggestions:\n{suggestions}\n\nProduce the optimized query, explain all changes, and estimate credit savings."}
    ]
    response = client.chat(messages, temperature=0.1)
    content = client.extract_content(response)
    usage = client.extract_usage(response)
    _log_agent_done(content, usage)
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
