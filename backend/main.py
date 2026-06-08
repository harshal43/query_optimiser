"""Query Optimization System – FastAPI entry point.

Run with: uvicorn backend.main:app --reload --port 8000
(from the project root: query_optimization/)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router

app = FastAPI(
    title="Query Optimization System",
    description=(
        "LLM-powered Snowflake SQL optimizer. "
        "Accepts raw SQL queries and returns optimization suggestions, "
        "an optimized query, token usage, and cost metrics."
    ),
    version="1.0.0",
)

# ------------------------------------------------------------
# CORS — allow the React dev server (and any origin in dev mode)
# ------------------------------------------------------------
# tighten to ["http://localhost:5173"] in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "query-optimization-backend"}
