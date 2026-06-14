from __future__ import annotations
import time
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    name: str = "base"
    version: str = "0.1.0"

    def __init__(self) -> None:
        self._call_count = 0
        self._error_count = 0
        self._total_ms = 0.0

    @abstractmethod
    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        ...

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        t0 = time.perf_counter()
        try:
            result = await self.process(state)
            self._call_count += 1
            return result
        except Exception as e:
            self._error_count += 1
            logger.error("%s failed: %s", self.name, e, exc_info=True)
            return {**state, "error": str(e)}
        finally:
            self._total_ms += (time.perf_counter() - t0) * 1000

    def health_check(self) -> dict[str, Any]:
        return {
            "agent": self.name,
            "version": self.version,
            "calls": self._call_count,
            "errors": self._error_count,
            "avg_ms": round(self._total_ms / max(self._call_count, 1), 1),
        }
