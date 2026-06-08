"""Agent 2 - Query Optimizer

Input: Original SQL + optimization suggestions from Agent 1
Output: Optimized Snowflake SQL + explanation + estimated credit savings %
Tracks: prompt_tokens, completion_tokens, total_tokens, cost
"""

import re
from ..llm.client import LLMClient
from ..llm.cost import calculate_cost

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
# Response parsing helpers
# ------------------------------------------------------------

def extract_sql(content: str) -> str:
    """Pull the SQL block between ```sql ... ```"""
    match = re.search(r'```sql\s*(.*?)\s*```', content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: everything between OPTIMIZED_QUERY: and EXPLANATION:
    match = re.search(r'OPTIMIZED_QUERY:\s*(.*?)(?=EXPLANATION:|$)', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content.strip()

def extract_explanation(content: str) -> str:
    """Pull the text between EXPLANATION: and CREDIT_SAVINGS_ESTIMATE:"""
    match = re.search(r'EXPLANATION:\s*(.*?)(?=CREDIT_SAVINGS_ESTIMATE:|$)', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: everything after EXPLANATION:
    match = re.search(r'EXPLANATION:\s*(.*)', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

def extract_credit_savings(content: str) -> dict:
    """Pull the estimated credit savings percentage and its reasoning.
    Returns { "percentage": float, "reasoning": str }
    """
    pct = 0.0
    reasoning = ""

    match = re.search(r'CREDIT_SAVINGS_ESTIMATE:\s*(\d+(?:\.\d+)?)', content, re.IGNORECASE)
    if match:
        pct = min(float(match.group(1)), 95.0)  # cap at 95 %

    reasoning_match = re.search(r'CREDIT_SAVINGS_ESTIMATE:.*?Reasoning:\s*(.*?)$', content, re.DOTALL | re.IGNORECASE)
    if reasoning_match:
        reasoning = reasoning_match.group(1).strip()

    return {"percentage": round(pct, 2), "reasoning": reasoning}

# ------------------------------------------------------------
# Agent runner
# ------------------------------------------------------------

def run_optimizer_agent(
    client: LLMClient,
    original_query: str,
    suggestions: str,
) -> dict:
    """Run the Query Optimizer agent.

    Returns:
        {
            "optimized_query": str,
            "explanation": str,
            "credit_savings": { "percentage": float, "reasoning": str },
            "raw_response": str,
            "token_usage": { prompt_tokens, completion_tokens, total_tokens, prompt_cost, completion_cost, total_cost, raw_usage }
        }
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
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
