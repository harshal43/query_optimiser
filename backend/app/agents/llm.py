from __future__ import annotations
import asyncio
import logging
import time
from typing import Any, Optional

import requests
from langchain_core.language_models import LLM

logger = logging.getLogger(__name__)

_FAILURE_WINDOW = 60.0
_FAILURE_LIMIT = 5
_failures: list[float] = []


class CustomLLM(LLM):
    """Unified LLM wrapper — same endpoint for all models, routed by model name."""

    model: str
    endpoint_url: str
    api_key: str
    temperature: float = 0.3
    top_p: float = 1.0
    max_tokens: int = 2000

    def _call(self, prompt: str, stop: Optional[list[str]] = None) -> str:
        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key,
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }
        if stop:
            payload["stop"] = stop
        response = requests.post(self.endpoint_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    @property
    def _llm_type(self) -> str:
        return "custom-llm"


def _circuit_open() -> bool:
    now = time.time()
    cutoff = now - _FAILURE_WINDOW
    recent = [t for t in _failures if t > cutoff]
    _failures[:] = recent
    return len(recent) >= _FAILURE_LIMIT


def _record_failure() -> None:
    _failures.append(time.time())


def _get_api_key(model: str) -> str:
    """Resolve per-model API key from settings based on model name prefix."""
    from app.config import settings
    m = model.lower()
    if m.startswith("claude"):
        return settings.anthropic_api_key
    if m.startswith("gpt") or m.startswith("o1") or m.startswith("o3"):
        return settings.openai_api_key
    if m.startswith("gemini"):
        return settings.google_api_key
    return ""


def get_llm(model: str | None = None, temperature: float = 0.3) -> CustomLLM | None:
    """Return a CustomLLM if API_URL and matching model API key are configured, else None."""
    from app.config import settings
    from app.services.admin_config import get_config
    if not settings.api_url:
        return None
    cfg = get_config()
    resolved_model = model or cfg.get("llm_primary") or "claude-sonnet-4"
    api_key = _get_api_key(str(resolved_model))
    if not api_key:
        logger.warning("No API key configured for model '%s' — skipping LLM", resolved_model)
        return None
    return CustomLLM(
        model=str(resolved_model),
        endpoint_url=settings.api_url,
        api_key=api_key,
        temperature=temperature,
    )


async def llm_call(prompt: str, model: str | None = None, temperature: float = 0.3) -> str | None:
    """
    Async wrapper around CustomLLM._call. Returns None if:
    - LLM not configured (no API_URL/API_KEY)
    - Circuit breaker open (≥5 failures in 60s)
    - Call fails (records failure, returns None)
    """
    if _circuit_open():
        logger.warning("LLM circuit breaker open — skipping call")
        return None
    llm = get_llm(model=model, temperature=temperature)
    if llm is None:
        return None
    try:
        result = await asyncio.get_event_loop().run_in_executor(None, lambda: llm._call(prompt))
        return result
    except Exception as e:
        _record_failure()
        logger.warning("LLM call failed (%s): %s", llm.model, e)
        return None
