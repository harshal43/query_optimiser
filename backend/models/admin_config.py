from pydantic import BaseModel


class AdvisorRules(BaseModel):
    detect_select_star: bool = True
    detect_unnecessary_distinct: bool = True
    detect_cartesian_joins: bool = True
    suggest_partition_pruning: bool = True
    suggest_clustering: bool = True
    suggest_removing_redundant_order_by: bool = True
    suggest_avoiding_unnecessary_ctes: bool = False
    detect_redundant_joins: bool = True
    detect_unused_ctes: bool = True
    suggest_column_pruning: bool = True
    suggest_filter_pushdown: bool = True
    suggest_result_cache_usage: bool = True


class OptimizerRules(BaseModel):
    rewrite_union_to_union_all: bool = True
    push_predicates_earlier: bool = True
    simplify_case_expressions: bool = True
    remove_redundant_order_by: bool = False
    eliminate_unnecessary_distinct: bool = True
    simplify_nested_subqueries: bool = True
    remove_unused_columns: bool = True
    rewrite_correlated_subqueries: bool = True


class SafetyRules(BaseModel):
    preserve_query_semantics: bool = True
    preserve_output_order: bool = True


class OutputRules(BaseModel):
    generate_change_summary: bool = True


class TierPreset(BaseModel):
    advisor_rules: AdvisorRules = AdvisorRules()
    optimizer_rules: OptimizerRules = OptimizerRules()
    safety_rules: SafetyRules = SafetyRules()


def _conservative() -> TierPreset:
    return TierPreset(
        advisor_rules=AdvisorRules(
            suggest_clustering=False,
            suggest_removing_redundant_order_by=False,
            suggest_avoiding_unnecessary_ctes=False,
        ),
        optimizer_rules=OptimizerRules(
            rewrite_union_to_union_all=False,
            remove_redundant_order_by=False,
            simplify_nested_subqueries=False,
            rewrite_correlated_subqueries=False,
        ),
        safety_rules=SafetyRules(
            preserve_query_semantics=True,
            preserve_output_order=True,
        ),
    )


def _balanced() -> TierPreset:
    return TierPreset(
        advisor_rules=AdvisorRules(
            suggest_avoiding_unnecessary_ctes=False,
        ),
        optimizer_rules=OptimizerRules(
            remove_redundant_order_by=False,
            rewrite_correlated_subqueries=False,
        ),
        safety_rules=SafetyRules(
            preserve_query_semantics=True,
            preserve_output_order=True,
        ),
    )


def _aggressive() -> TierPreset:
    return TierPreset(
        advisor_rules=AdvisorRules(
            suggest_avoiding_unnecessary_ctes=True,
        ),
        optimizer_rules=OptimizerRules(
            remove_redundant_order_by=True,
            rewrite_correlated_subqueries=True,
        ),
        safety_rules=SafetyRules(
            preserve_query_semantics=True,
            preserve_output_order=False,
        ),
    )


def _default_tier_configs() -> dict:
    return {
        "conservative": _conservative(),
        "balanced": _balanced(),
        "aggressive": _aggressive(),
    }


class AdminConfig(BaseModel):
    model_config = {"extra": "ignore"}

    tier_configs: dict[str, TierPreset] = None  # type: ignore
    output_rules: OutputRules = OutputRules()
    default_tier: str = "balanced"
    additional_llm_instructions: str = ""

    def model_post_init(self, __context):
        if self.tier_configs is None:
            object.__setattr__(self, "tier_configs", _default_tier_configs())
