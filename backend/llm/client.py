"""OpenAI-compatible LLM HTTP client with provider-aware auth."""

import httpx
from typing import Any, Dict, List


def _provider(model: str) -> str:
    return "anthropic" if model.startswith("claude") else "openai"


class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 120.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.endpoint = self._resolve_endpoint(base_url)
        self._provider = _provider(model)

    @staticmethod
    def _resolve_endpoint(base_url: str) -> str:
        url = base_url.rstrip("/")
        if url.endswith("/chat/completions"):
            return url
        return f"{url}/chat/completions"

    def _headers(self) -> Dict[str, str]:
        if self._provider == "anthropic":
            return {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "anthropic-version": "2023-06-01",
            }
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-API-KEY": self.api_key,
        }

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.endpoint, headers=self._headers(), json=payload)
            response.raise_for_status()
            return response.json()

    def extract_content(self, response: Dict[str, Any]) -> str:
        # OpenAI-compat format
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            pass
        # Anthropic native format fallback
        try:
            return response["content"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise ValueError(f"Unexpected LLM response structure: {exc}\n{response}")

    def extract_usage(self, response: Dict[str, Any]) -> Dict[str, int]:
        usage = response.get("usage", {})

        def _pick(d: dict, *keys: str, default: int = 0) -> int:
            for k in keys:
                v = d.get(k)
                if v is not None:
                    try:
                        return int(v)
                    except (TypeError, ValueError):
                        pass
            return default

        prompt = _pick(
            usage,
            "prompt_tokens",
            "input_tokens",
            "promptTokens",
            "prompt_token_count",
        )
        completion = _pick(
            usage,
            "completion_tokens",
            "output_tokens",
            "completionTokens",
            "completion_token_count",
        )
        total = _pick(usage, "total_tokens", "totalTokens", default=prompt + completion) or (prompt + completion)

        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
            "raw_usage": usage,
        }
