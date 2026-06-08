"""OpenAI-compatible LLM HTTP client.

Supports any endpoint that follows the OpenAI Chat Completions format, including standard OpenAI, Azure OpenAI, and routed endpoints such as Coforge TrustAI (quasarmarket.coforge.com).

Auth: sends BOTH Authorization: Bearer AND X-API-KEY headers so the client works with any flavour of OpenAI-compatible gateway without user configuration.
"""

import httpx
from typing import Any, Dict, List

class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 120.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.endpoint = self._resolve_endpoint(base_url)

    # ------------------------------------------------------------
    # Endpoint resolution
    # ------------------------------------------------------------

    @staticmethod
    def _resolve_endpoint(base_url: str) -> str:
        """Accept either:
        - A full URL already ending with /chat/completions
        - A base URL like https://api.openai.com/v1 (appends /chat/completions)
        """
        url = base_url.rstrip("/")
        if url.endswith("/chat/completions"):
            return url
        return f"{url}/chat/completions"

    # ------------------------------------------------------------
    # Core chat method
    # ------------------------------------------------------------

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-API-KEY": self.api_key,
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.endpoint, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    # ------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------

    def extract_content(self, response: Dict[str, Any]) -> str:
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ValueError(f"Unexpected LLM response structure: {exc}\n{response}")

    def extract_usage(self, response: Dict[str, Any]) -> Dict[str, int]:
        """Extract token counts from the response.

        Different LLM gateways use different field names for the same data.
        We try every known variant so routed endpoints (Coforge, Azure, etc.)
        all work without extra configuration.

        Variants tried (in priority order):
            prompt -> prompt_tokens | input_tokens | promptTokens
            completion -> completion_tokens | output_tokens | completionTokens
            total -> total_tokens | totalTokens (or computed as sum)
        """
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
            "generated_tokens",
        )
        completion = _pick(
            usage,
            "completion_tokens",
            "output_tokens",
            "completionTokens",
            "completion_token_count",
        )
        total = _pick(
            usage,
            "total_tokens",
            "totalTokens",
            default=prompt + completion,
        ) or (prompt + completion)

        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
            "raw_usage": usage,
        }
