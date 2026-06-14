from __future__ import annotations
import logging
from typing import Any

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class PatternLearnerAgent(BaseAgent):
    name = "pattern_learner"

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        logger.info(
            "PatternLearner: recording optimization pattern",
            extra={
                "classification": state.get("classification"),
                "risk_score": state.get("risk_score"),
                "variants_count": len(state.get("variants", [])),
            }
        )
        return state
