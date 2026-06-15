import pytest
from backend.agents.advisor import _build_advisor_suffix
from backend.agents.optimizer import _build_optimizer_suffix
from backend.models.admin_config import AdminConfig


def _config():
    return AdminConfig()


def test_advisor_suffix_uses_conservative_rules():
    config = _config()
    suffix = _build_advisor_suffix(config, "conservative")
    # conservative has suggest_clustering=False — must NOT appear
    assert "clustering" not in suffix
    # conservative has suggest_partition_pruning=True — must appear
    assert "partition pruning" in suffix.lower()


def test_advisor_suffix_uses_aggressive_rules():
    config = _config()
    suffix = _build_advisor_suffix(config, "aggressive")
    # aggressive has suggest_avoiding_unnecessary_ctes=True
    assert "unnecessary ctes" in suffix.lower()


def test_advisor_suffix_uses_default_tier_on_unknown_strategy():
    config = _config()
    suffix = _build_advisor_suffix(config, "nonexistent_tier")
    # should not raise — falls back to default_tier
    assert isinstance(suffix, str)


def test_optimizer_suffix_uses_conservative_rules():
    config = _config()
    suffix = _build_optimizer_suffix(config, "conservative")
    # conservative has rewrite_correlated_subqueries=False — must NOT appear
    assert "correlated" not in suffix


def test_optimizer_suffix_uses_aggressive_rules():
    config = _config()
    suffix = _build_optimizer_suffix(config, "aggressive")
    # aggressive has rewrite_correlated_subqueries=True
    assert "correlated" in suffix


def test_advisor_suffix_has_no_optimization_goal_label():
    config = _config()
    suffix = _build_advisor_suffix(config, "balanced")
    assert "Optimization Goal" not in suffix
    assert "lowest_credits" not in suffix
    assert "fastest_performance" not in suffix


def test_optimizer_suffix_has_no_optimization_goal_label():
    config = _config()
    suffix = _build_optimizer_suffix(config, "balanced")
    assert "Primary Objective" not in suffix
    assert "lowest_credits" not in suffix
