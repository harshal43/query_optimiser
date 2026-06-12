from pydantic import BaseModel


class AdvisorRules(BaseModel):
    # Existing
    detect_select_star: bool = True
    detect_unnecessary_distinct: bool = True
    detect_cartesian_joins: bool = True
    suggest_partition_pruning: bool = True
    suggest_clustering: bool = True
    suggest_removing_redundant_order_by: bool = True
    suggest_avoiding_unnecessary_ctes: bool = False
    # New
    detect_redundant_joins: bool = True
    detect_unused_ctes: bool = True
    suggest_column_pruning: bool = True
    suggest_filter_pushdown: bool = True
    suggest_result_cache_usage: bool = True


class OptimizerRules(BaseModel):
    # Existing
    rewrite_union_to_union_all: bool = True
    push_predicates_earlier: bool = True
    simplify_case_expressions: bool = True
    remove_redundant_order_by: bool = False
    eliminate_unnecessary_distinct: bool = True
    simplify_nested_subqueries: bool = True
    # New
    remove_unused_columns: bool = True
    rewrite_correlated_subqueries: bool = True


class SafetyRules(BaseModel):
    preserve_query_semantics: bool = True
    preserve_output_order: bool = True


class OutputRules(BaseModel):
    generate_change_summary: bool = True


class AdminConfig(BaseModel):
    advisor_rules: AdvisorRules = AdvisorRules()
    optimizer_rules: OptimizerRules = OptimizerRules()
    safety_rules: SafetyRules = SafetyRules()
    output_rules: OutputRules = OutputRules()
    optimization_goal: str = "lowest_credits"   # lowest_credits | fastest_performance | balanced
    aggressiveness: str = "moderate"             # conservative | moderate | aggressive
    additional_llm_instructions: str = ""
