from __future__ import annotations
from typing import Any

from app.agents.base import BaseAgent


class CostEstimatorAgent(BaseAgent):
    name = "cost_estimator"

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        metrics = state.get("execution_metrics", {})
        variants = state.get("variants", [])

        original_credits = float(metrics.get("credits_used", 0) or 0)
        original_ms = float(metrics.get("execution_time_ms", 0) or 0)
        original_bytes = int(metrics.get("bytes_scanned", 0) or 0)

        variant_predictions: list[dict[str, Any]] = []
        for v in variants:
            details = v.get("technique_details", [])
            total_pct = sum(d.get("avg_credit_reduction_pct", 0) for d in details)
            reduction_pct = min(total_pct, 80)
            predicted_credits = original_credits * (1 - reduction_pct / 100)
            predicted_ms = original_ms * (1 - reduction_pct / 100 * 0.7)

            confidence = "HIGH" if len(details) > 0 and original_credits > 1 else "MEDIUM" if original_credits > 0 else "LOW"
            ci_lower = predicted_credits * 0.8
            ci_upper = predicted_credits * 1.3

            variant_predictions.append({
                "variant_id": v["id"],
                "original_credits": original_credits,
                "predicted_credits": round(predicted_credits, 4),
                "savings_credits": round(original_credits - predicted_credits, 4),
                "savings_pct": round(reduction_pct, 1),
                "predicted_ms": round(predicted_ms, 0),
                "confidence": confidence,
                "ci_lower": round(ci_lower, 4),
                "ci_upper": round(ci_upper, 4),
                "technique_attribution": [
                    {"technique": d["name"], "credit_reduction_pct": d["avg_credit_reduction_pct"]}
                    for d in details
                ],
            })

        cost_predictions = {
            "original_credits": original_credits,
            "original_ms": original_ms,
            "original_bytes_scanned": original_bytes,
            "variants": variant_predictions,
        }

        return {**state, "cost_predictions": cost_predictions}
