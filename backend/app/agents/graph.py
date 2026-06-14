from __future__ import annotations
from typing import Any

from langgraph.graph import StateGraph, END

from app.agents.analyzer import AnalyzerAgent
from app.agents.optimizer import OptimizerAgent
from app.agents.cost_estimator import CostEstimatorAgent
from app.agents.validator import ValidatorAgent
from app.agents.pattern_learner import PatternLearnerAgent
from app.agents.standardizer import StandardizerAgent
from app.models.optimization import OptimizationState

_analyzer = AnalyzerAgent()
_optimizer = OptimizerAgent()
_cost_estimator = CostEstimatorAgent()
_validator = ValidatorAgent()
_pattern_learner = PatternLearnerAgent()
_standardizer = StandardizerAgent()


async def _analyze(state: OptimizationState) -> OptimizationState:
    return await _analyzer.run(dict(state))  # type: ignore[return-value]


async def _optimize(state: OptimizationState) -> OptimizationState:
    return await _optimizer.run(dict(state))  # type: ignore[return-value]


async def _estimate_cost(state: OptimizationState) -> OptimizationState:
    return await _cost_estimator.run(dict(state))  # type: ignore[return-value]


async def _validate(state: OptimizationState) -> OptimizationState:
    return await _validator.run(dict(state))  # type: ignore[return-value]


async def _standardize(state: OptimizationState) -> OptimizationState:
    return await _standardizer.run(dict(state))  # type: ignore[return-value]


def _build_graph() -> Any:
    builder: StateGraph = StateGraph(OptimizationState)  # type: ignore[type-arg]
    builder.add_node("analyzer", _analyze)
    builder.add_node("optimizer", _optimize)
    builder.add_node("cost_estimator", _estimate_cost)
    builder.add_node("validator", _validate)
    builder.add_node("standardizer", _standardize)

    builder.set_entry_point("analyzer")
    builder.add_edge("analyzer", "optimizer")
    builder.add_edge("optimizer", "cost_estimator")
    builder.add_edge("cost_estimator", "validator")
    builder.add_edge("validator", "standardizer")
    builder.add_edge("standardizer", END)

    return builder.compile()


_graph = _build_graph()


async def run_optimization_pipeline(
    query_id: str,
    query_text: str,
    query_hash: str,
    classification: str | None,
    severity: str | None,
    execution_metrics: dict[str, Any],
) -> OptimizationState:
    initial: OptimizationState = {
        "query_id": query_id,
        "query_text": query_text,
        "query_hash": query_hash,
        "classification": classification,
        "severity": severity,
        "execution_metrics": execution_metrics,
        "diagnosis": {},
        "variants": [],
        "cost_predictions": {},
        "validation_results": {},
        "risk_score": 0,
        "recommended_variant": None,
        "error": None,
    }
    result = await _graph.ainvoke(initial)
    return result


def agent_health() -> dict[str, Any]:
    return {
        a.name: a.health_check()
        for a in [_analyzer, _optimizer, _cost_estimator, _validator, _pattern_learner, _standardizer]
    }
