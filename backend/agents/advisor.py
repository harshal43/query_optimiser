"""Agent 1 - Query Optimization Advisor

Input: Raw Snowflake SQL query
Output: Numbered optimization suggestions (raw text + parsed list)
"""

import re
from ..llm.client import LLMClient
from ..llm.cost import calculate_cost

# ------------------------------------------------------------
# Prompt
# ------------------------------------------------------------

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

# ------------------------------------------------------------
# Suggestion parser
# ------------------------------------------------------------

def parse_suggestions(raw: str) -> list:
    """Split the raw suggestion text into individual structured items.
    Each item: { number, title, body, full_text }
    """
    # Strip "SUGGESTIONS:" header if present
    text = re.sub(r'(?i)^SUGGESTIONS:\s*', '', raw.strip())

    # Split on lines that start a new numbered item (e.g. "1.", "2.", ...)
    parts = re.split(r'\n(?=\d+\.)', text)

    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = re.match(r'^(\d+)\.\s*(.*?)\n(.*)', part, re.DOTALL)
        if not m:
            continue
        number = int(m.group(1))
        content = m.group(2).strip()
        lines = content.split('\n')
        title = lines[0].strip()
        body = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''
        result.append({
            "number": number,
            "title": title,
            "body": body,
            "full_text": f"{number}. {content}",
        })
    return result

# ------------------------------------------------------------
# Agent runner
# ------------------------------------------------------------

def run_advisor_agent(client: LLMClient, query: str) -> dict:
    """Run the Optimization Advisor agent.

    Returns:
        {
            "suggestions_raw": str,
            "parsed_suggestions": [ { number, title, body, full_text }, ... ],
            "token_usage": { ... }
        }
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
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
