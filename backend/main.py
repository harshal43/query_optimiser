"""Query Optimization System – FastAPI entry point.

Run with: uvicorn backend.main:app --reload --port 8000
(from the project root: query_optimization/)
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router
from .api.admin_routes import router as admin_router

# Our agent loggers at DEBUG; everything else stays at INFO so httpx/uvicorn aren't drowned out
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
for _name in (
    "backend.agents.advisor",
    "backend.agents.optimizer",
    "backend.agents.snowflake_context",
):
    logging.getLogger(_name).setLevel(logging.DEBUG)

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
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(admin_router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "query-optimization-backend"}
