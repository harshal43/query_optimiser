# Snowflake Query Optimiser — Project Narrative

## The Problem We're Solving

Every day, data teams write SQL queries that cost more than they should. A `SELECT *` on a billion-row table. A `YEAR(created_at)` function that disables partition pruning. A cartesian join that nobody caught in code review. These aren't just style issues — each one translates directly into wasted Snowflake credits and slower dashboards.

At scale, manually reviewing queries becomes impossible. You can't put a senior Snowflake engineer on every pull request. The Query Optimiser exists to automate that expertise — to catch what humans miss, rewrite what machines can handle, and loop in people only when domain knowledge is actually required.

---

## What We Built

A full-stack application that takes inefficient Snowflake SQL and returns optimized, schema-validated, performance-tested alternatives.

**The frontend** is a React SPA where analysts load queries, review AI-generated suggestions, resolve human-in-the-loop flags, and compare before/after execution metrics side by side.

**The backend** is a FastAPI service running a four-agent LLM pipeline, with live Snowflake connectivity and a configurable rule engine.

**The intelligence layer** is model-agnostic — Claude, GPT-4o, or Gemini — with per-request switching and streaming responses.

---

## The Four-Agent Pipeline

The system isn't a single prompt asking an LLM to "make this faster." It's four specialised agents with distinct responsibilities:

### Agent 1 — The Advisor

Reads the query and the active strategy tier, then produces a numbered list of optimization opportunities ordered by estimated impact. It detects anti-patterns like `SELECT *`, non-sargable predicates, missing filters, and cartesian joins. When it encounters something it can't resolve without business context — *which* columns are actually needed? *what* date range is intended? — it emits a HITL flag rather than guessing.

### Agent 2 — The Optimizer

Rewrites the SQL using only the suggestions the user selected. It operates under a strict constraint: every column and table must exist in the live Snowflake schema. After generation, `sqlglot` parses the output and flags any hallucinated columns as warnings. No invented fields slip through.

### Agent 3 — The Context Fetcher

Runs silently before the other agents. It extracts table names from the query, hits `INFORMATION_SCHEMA` for columns, data types, clustering keys, and row counts, then injects that metadata into the prompts. Results are TTL-cached to avoid hammering Snowflake.

### Agent 4 — The Query Runner

Executes both the original and optimized queries, pulls real KPIs from `QUERY_HISTORY` — elapsed time, bytes scanned, partitions touched, credits consumed — and surfaces the delta. Only `SELECT` statements are accepted, with an automatic `LIMIT 100` guard.

---

## Strategy Tiers: Not One Size Fits All

Users qualify their intent across two dimensions — **Priority** (cost, balanced, speed) and **Tolerance** (minimal change, standard, major restructure) — which map to one of three tiers:

| Tier | Character |
|---|---|
| **Conservative** | Safe rewrites only. Structure preserved. Output ordering guaranteed. |
| **Balanced** | Standard optimizations. Moderate rewrites. Clustering key exploitation enabled. |
| **Aggressive** | Maximum optimization. Correlated subqueries flattened, redundant `ORDER BY` removed, CTEs eliminated if unused. |

Each tier has its own rulebook for what the Advisor detects and what the Optimizer applies. Admins can toggle individual rules without touching code.

---

## Human-in-the-Loop: Knowing When to Ask

The system doesn't pretend to know your business. When the Advisor sees `SELECT *`, it asks which columns are needed. When it sees a missing `WHERE` clause on a large table, it asks what filter should apply. These flags surface as interactive inputs in the UI. The user's answers are prepended to the Optimizer's context, so the rewritten SQL incorporates real domain knowledge — not LLM hallucination.

---

## The Batch Reality

For teams with hundreds of queries, the system supports batch processing: upload an Excel or CSV, run parallel analysis (capped at 5 concurrent LLM calls), review per-query suggestions, batch-optimize, and export everything back to Excel. Cost tracking is transparent — every LLM call records token usage and USD spend, surfaced per optimization session.

---

## Technical Guardrails

| Guardrail | Mechanism |
|---|---|
| **Schema hallucination prevention** | Live metadata injected as strict prompt constraint + post-generation `sqlglot` validation |
| **Sandbox safety** | Agent 4 rejects non-`SELECT` statements and auto-injects `LIMIT 100` |
| **Session correctness** | `USE DATABASE` / `USE SCHEMA` issued before every query to prevent context errors |
| **Async safety** | All synchronous Snowflake I/O wrapped in `asyncio.to_thread()` |
| **Cache freshness** | Schema cache TTL of 5 minutes, invalidated on database/schema change |

---

## In One Sentence

The Snowflake Query Optimiser is an expert system that automates query performance analysis and rewriting through a multi-agent LLM pipeline, grounded in live schema data and constrained by configurable safety rules, with human input requested only when business context is irreplaceable.
