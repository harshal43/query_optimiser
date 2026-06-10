from pydantic import BaseModel


class AdvisorRules(BaseModel):
    detect_select_star: bool = True
    detect_unnecessary_distinct: bool = True
    detect_cartesian_joins: bool = True
    suggest_partition_pruning: bool = True
    suggest_clustering: bool = True
    suggest_removing_redundant_order_by: bool = True
    suggest_avoiding_unnecessary_ctes: bool = False


class OptimizerRules(BaseModel):
    rewrite_union_to_union_all: bool = True
    push_predicates_earlier: bool = True
    simplify_case_expressions: bool = True
    remove_redundant_order_by: bool = False
    eliminate_unnecessary_distinct: bool = True
    simplify_nested_subqueries: bool = True


class AdminConfig(BaseModel):
    advisor_rules: AdvisorRules = AdvisorRules()
    optimizer_rules: OptimizerRules = OptimizerRules()
    optimization_goal: str = "lowest_credits"        # lowest_credits | fastest_performance | balanced
    aggressiveness: str = "moderate"                  # conservative | moderate | aggressive
    additional_llm_instructions: str = ""
