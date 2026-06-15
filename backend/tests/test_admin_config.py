import pytest
from backend.models.admin_config import AdminConfig, TierPreset, AdvisorRules, OptimizerRules, SafetyRules


def test_tier_preset_exists():
    preset = TierPreset()
    assert hasattr(preset, 'advisor_rules')
    assert hasattr(preset, 'optimizer_rules')
    assert hasattr(preset, 'safety_rules')


def test_admin_config_has_tier_configs():
    config = AdminConfig()
    assert 'conservative' in config.tier_configs
    assert 'balanced' in config.tier_configs
    assert 'aggressive' in config.tier_configs


def test_admin_config_has_default_tier():
    config = AdminConfig()
    assert config.default_tier == 'balanced'


def test_admin_config_no_optimization_goal():
    config = AdminConfig()
    assert not hasattr(config, 'optimization_goal')


def test_admin_config_no_aggressiveness():
    config = AdminConfig()
    assert not hasattr(config, 'aggressiveness')


def test_conservative_preset_is_restrictive():
    config = AdminConfig()
    conservative = config.tier_configs['conservative']
    assert conservative.advisor_rules.suggest_clustering is False
    assert conservative.optimizer_rules.simplify_nested_subqueries is False
    assert conservative.optimizer_rules.rewrite_correlated_subqueries is False
    assert conservative.safety_rules.preserve_output_order is True


def test_aggressive_preset_is_permissive():
    config = AdminConfig()
    aggressive = config.tier_configs['aggressive']
    assert aggressive.advisor_rules.suggest_avoiding_unnecessary_ctes is True
    assert aggressive.optimizer_rules.rewrite_correlated_subqueries is True
    assert aggressive.optimizer_rules.remove_redundant_order_by is True
    assert aggressive.safety_rules.preserve_output_order is False


def test_old_config_json_without_tier_configs_loads_with_defaults():
    """Pydantic must accept old admin_config.json that has no tier_configs key."""
    old_data = {
        "advisor_rules": {"detect_select_star": True},
        "optimization_goal": "lowest_credits",
        "aggressiveness": "moderate",
        "additional_llm_instructions": "",
    }
    config = AdminConfig.model_validate(old_data)
    assert 'conservative' in config.tier_configs
    assert 'balanced' in config.tier_configs
    assert 'aggressive' in config.tier_configs
