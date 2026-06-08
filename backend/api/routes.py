import asyncio
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List

from ..models.schemas import QueryDetail, QueryListResponse, SnowflakeCredentials
from ..data.loader import get_query_ids, get_query, reload_cache, get_debug_info, load_from_upload, get_active_source
from ..data import snowflake_connector
from ..llm.client import LLMClient
from ..agents.advisor import run_advisor_agent, run_advisor_agent_async
from ..agents.optimizer import run_optimizer_agent, run_optimizer_agent_async
from ..config import SUPPORTED_MODELS, get_llm_credentials

router = APIRouter(prefix="/api", tags=["Query Optimization"])

# ------------------------------------------------------------
# Request models
# ------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    query_id: str
    model: str

class OptimizeRequest(BaseModel):
    query_id: str
    model: str
    selected_suggestions: List[str]

class AnalyzeCustomRequest(BaseModel):
    query_text: str
    credits: float = 0.0
    model: str

class OptimizeCustomRequest(BaseModel):
    query_text: str
    credits: float = 0.0
    model: str
    selected_suggestions: List[str]

class BatchAnalyzeRequest(BaseModel):
    query_ids: List[str]
    model: str

class BatchOptimizeItem(BaseModel):
    query_id: str
    selected_suggestions: List[str]

class BatchOptimizeRequest(BaseModel):
    items: List[BatchOptimizeItem]
    model: str

# ------------------------------------------------------------
# Query catalogue endpoints
# ------------------------------------------------------------

@router.get("/queries", response_model=QueryListResponse)
def list_queries():
    try:
        return {"query_ids": get_query_ids()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/queries/{query_id}", response_model=QueryDetail)
def get_query_detail(query_id: str):
    try:
        return get_query(query_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/reload-cache")
def reload_data_cache():
    reload_cache()
    return {"message": "Cache cleared. Data will be reloaded on next request."}

@router.get("/debug/excel")
def debug_excel():
    return get_debug_info()

@router.post("/debug/llm-test")
def debug_llm_test(request: dict):
    try:
        client = LLMClient(
            api_key=request["api_key"],
            base_url=request["base_url"],
            model=request.get("model", "gpt-4o"),
        )
        raw = client.chat(
            messages=[{"role": "user", "content": "Say the word OK only."}],
            max_tokens=5,
        )
        return {
            "full_response": raw,
            "usage_block": raw.get("usage"),
            "parsed_usage": client.extract_usage(raw),
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

@router.post("/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="Only .xlsx, .xls, or .csv files are accepted.")
    try:
        content = await file.read()
        result = load_from_upload(content, file.filename)
        return result
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to parse Excel file: {exc}")

@router.get("/data-source")
def data_source():
    return {"source": get_active_source()}

@router.get("/models")
def list_models():
    return {"models": SUPPORTED_MODELS}

# ------------------------------------------------------------
# Snowflake connector endpoints
# ------------------------------------------------------------

@router.post("/snowflake/connect")
def snowflake_connect(request: SnowflakeCredentials):
    try:
        snowflake_connector.connect(request.model_dump())
        return {
            "connected": True,
            "account": snowflake_connector.get_account(),
            "message": "Connected successfully",
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Connection failed: {exc}")


@router.get("/snowflake/status")
def snowflake_status():
    connected = snowflake_connector.is_connected()
    return {
        "connected": connected,
        "account": snowflake_connector.get_account() if connected else None,
        "message": f"Connected to {snowflake_connector.get_account()}" if connected else "Not connected",
    }


@router.post("/snowflake/disconnect")
def snowflake_disconnect():
    snowflake_connector.disconnect()
    return {"message": "Disconnected"}


@router.get("/snowflake/queries")
def snowflake_queries(category: str = "all"):
    if not snowflake_connector.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Not connected to Snowflake. Call POST /api/snowflake/connect first.",
        )
    try:
        rows = snowflake_connector.fetch_queries(category)
        return {"category": category, "rows": rows, "count": len(rows)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Query failed: {exc}")

# ------------------------------------------------------------
# Step 1 — Analyze: run Agent 1, return parsed suggestions
# ------------------------------------------------------------

@router.post("/analyze")
async def analyze_query(request: AnalyzeRequest):
    if request.model not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{request.model}' not supported. Choose from: {SUPPORTED_MODELS}",
        )
    try:
        query_data = get_query(request.query_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    try:
        creds = get_llm_credentials(request.model)
        client = LLMClient(api_key=creds["api_key"], base_url=creds["base_url"], model=request.model)
        advisor_result = await run_advisor_agent_async(client, query_data["query_text"])
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Advisor agent failed: {exc}")

    return {
        "query_id": request.query_id,
        "original_query": query_data["query_text"],
        "credits": query_data["credits"],
        "suggestions_raw": advisor_result["suggestions_raw"],
        "parsed_suggestions": advisor_result["parsed_suggestions"],
    }

# ------------------------------------------------------------
# Step 2 — Optimize: run Agent 2 with only the user-selected suggestions
# ------------------------------------------------------------

@router.post("/optimize")
async def optimize_query(request: OptimizeRequest):
    if request.model not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{request.model}' not supported. Choose from: {SUPPORTED_MODELS}",
        )
    if not request.selected_suggestions:
        raise HTTPException(
            status_code=400,
            detail="No suggestions selected. Please select at least one suggestion.",
        )
    try:
        query_data = get_query(request.query_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    original_query: str = query_data["query_text"]
    credits: float = query_data["credits"]
    selected_text = "\n\n".join(request.selected_suggestions)

    try:
        creds = get_llm_credentials(request.model)
        client = LLMClient(api_key=creds["api_key"], base_url=creds["base_url"], model=request.model)
        optimizer_result = await run_optimizer_agent_async(client, original_query, selected_text)
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Optimizer agent failed: {exc}")

    savings = optimizer_result.get("credit_savings", {})
    savings_pct = savings.get("percentage", 0.0)
    estimated_optimized_credits = round(credits * (1 - savings_pct / 100), 6)
    credits_saved = round(credits - estimated_optimized_credits, 6)

    return {
        "query_id": request.query_id,
        "original_query": original_query,
        "optimizer_result": optimizer_result,
        "cost_comparison": {
            "original_credits": credits,
            "estimated_optimized_credits": estimated_optimized_credits,
            "credits_saved": credits_saved,
            "savings_percentage": round(savings_pct, 2),
            "savings_reasoning": savings.get("reasoning", ""),
        },
    }

# ------------------------------------------------------------
# Custom query endpoints (no Excel / query catalogue required)
# ------------------------------------------------------------

@router.post("/analyze-custom")
async def analyze_custom_query(request: AnalyzeCustomRequest):
    if request.model not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{request.model}' not supported. Choose from: {SUPPORTED_MODELS}",
        )
    if not request.query_text.strip():
        raise HTTPException(status_code=400, detail="query_text must not be empty.")

    try:
        creds = get_llm_credentials(request.model)
        client = LLMClient(api_key=creds["api_key"], base_url=creds["base_url"], model=request.model)
        advisor_result = await run_advisor_agent_async(client, request.query_text)
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Advisor agent failed: {exc}")

    return {
        "query_id": "custom",
        "original_query": request.query_text,
        "credits": request.credits,
        "suggestions_raw": advisor_result["suggestions_raw"],
        "parsed_suggestions": advisor_result["parsed_suggestions"],
    }

@router.post("/optimize-custom")
async def optimize_custom_query(request: OptimizeCustomRequest):
    if request.model not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{request.model}' not supported. Choose from: {SUPPORTED_MODELS}",
        )
    if not request.selected_suggestions:
        raise HTTPException(
            status_code=400,
            detail="No suggestions selected. Please select at least one suggestion.",
        )
    if not request.query_text.strip():
        raise HTTPException(status_code=400, detail="query_text must not be empty.")

    selected_text = "\n\n".join(request.selected_suggestions)
    credits = request.credits

    try:
        creds = get_llm_credentials(request.model)
        client = LLMClient(api_key=creds["api_key"], base_url=creds["base_url"], model=request.model)
        optimizer_result = await run_optimizer_agent_async(client, request.query_text, selected_text)
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Optimizer agent failed: {exc}")

    savings = optimizer_result.get("credit_savings", {})
    savings_pct = savings.get("percentage", 0.0)
    estimated_optimized_credits = round(credits * (1 - savings_pct / 100), 6)
    credits_saved = round(credits - estimated_optimized_credits, 6)

    return {
        "query_id": "custom",
        "original_query": request.query_text,
        "optimizer_result": optimizer_result,
        "cost_comparison": {
            "original_credits": credits,
            "estimated_optimized_credits": estimated_optimized_credits,
            "credits_saved": credits_saved,
            "savings_percentage": round(savings_pct, 2),
            "savings_reasoning": savings.get("reasoning", ""),
        },
    }

# ------------------------------------------------------------
# Batch endpoints — parallel execution with concurrency cap
# ------------------------------------------------------------

_BATCH_SEM_SIZE = 5


@router.post("/batch-analyze")
async def batch_analyze(request: BatchAnalyzeRequest):
    if request.model not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model '{request.model}' not supported.")
    try:
        creds = get_llm_credentials(request.model)
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    sem = asyncio.Semaphore(_BATCH_SEM_SIZE)

    async def analyze_one(qid: str) -> dict:
        async with sem:
            try:
                query_data = get_query(qid)
                client = LLMClient(api_key=creds["api_key"], base_url=creds["base_url"], model=request.model)
                result = await run_advisor_agent_async(client, query_data["query_text"])
                return {
                    "query_id": qid,
                    "success": True,
                    "original_query": query_data["query_text"],
                    "credits": query_data["credits"],
                    "suggestions_raw": result["suggestions_raw"],
                    "parsed_suggestions": result["parsed_suggestions"],
                }
            except Exception as exc:
                return {"query_id": qid, "success": False, "error": str(exc)}

    results = await asyncio.gather(*[analyze_one(qid) for qid in request.query_ids])
    return {"results": list(results), "total": len(results), "model": request.model}


@router.post("/batch-optimize")
async def batch_optimize(request: BatchOptimizeRequest):
    if request.model not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model '{request.model}' not supported.")
    try:
        creds = get_llm_credentials(request.model)
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    sem = asyncio.Semaphore(_BATCH_SEM_SIZE)

    async def optimize_one(item: BatchOptimizeItem) -> dict:
        async with sem:
            try:
                query_data = get_query(item.query_id)
                original_query = query_data["query_text"]
                credits = query_data["credits"]
                selected_text = "\n\n".join(item.selected_suggestions)
                client = LLMClient(api_key=creds["api_key"], base_url=creds["base_url"], model=request.model)
                result = await run_optimizer_agent_async(client, original_query, selected_text)
                savings_pct = result.get("credit_savings", {}).get("percentage", 0.0)
                est_credits = round(credits * (1 - savings_pct / 100), 6)
                return {
                    "query_id": item.query_id,
                    "success": True,
                    "original_query": original_query,
                    "optimizer_result": result,
                    "cost_comparison": {
                        "original_credits": credits,
                        "estimated_optimized_credits": est_credits,
                        "credits_saved": round(credits - est_credits, 6),
                        "savings_percentage": round(savings_pct, 2),
                        "savings_reasoning": result.get("credit_savings", {}).get("reasoning", ""),
                    },
                }
            except Exception as exc:
                return {"query_id": item.query_id, "success": False, "error": str(exc)}

    results = await asyncio.gather(*[optimize_one(item) for item in request.items])
    return {"results": list(results), "total": len(results), "model": request.model}
