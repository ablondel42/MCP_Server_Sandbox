"""Graph query layer for symbol and edge retrieval."""

from repo_context.graph.queries import (
    get_symbol,
    get_symbol_by_qualified_name,
    find_symbols_by_name,
    get_parent_symbol,
    get_child_symbols,
    get_lexical_parent_symbol,
    get_lexical_child_symbols,
    get_outgoing_edges,
    get_incoming_edges,
    get_symbols_for_file,
    get_repo_graph_stats,
    CALLABLE_KINDS,
    LOCAL_CALLABLE_KINDS,
)
from repo_context.graph.references import (
    list_reference_edges_for_target,
    list_referenced_by,
    list_references_from_symbol,
    build_reference_stats,
    get_reference_refresh_state,
)
from repo_context.graph.risk_engine import (
    analyze_symbol_risk,
    analyze_target_set_risk,
)
from repo_context.graph.risk_types import (
    RiskTarget,
    RiskFacts,
    RiskResult,
)
from repo_context.graph.risk_rules import (
    ISSUE_STALE_CONTEXT,
    ISSUE_LOW_CONFIDENCE_MATCH,
    ISSUE_HIGH_REFERENCE_COUNT,
    ISSUE_CROSS_FILE_IMPACT,
    ISSUE_CROSS_MODULE_IMPACT,
    ISSUE_PUBLIC_SURFACE_CHANGE,
    ISSUE_INHERITANCE_RISK,
    ISSUE_MULTI_FILE_CHANGE,
    ISSUE_MULTI_MODULE_CHANGE,
    ISSUE_REFERENCE_DATA_UNAVAILABLE,
)
from repo_context.graph.risk_scoring import (
    DECISION_SAFE_ENOUGH,
    DECISION_REVIEW_REQUIRED,
    DECISION_HIGH_RISK,
)

__all__ = [
    "get_symbol",
    "get_symbol_by_qualified_name",
    "find_symbols_by_name",
    "get_parent_symbol",
    "get_child_symbols",
    "get_lexical_parent_symbol",
    "get_lexical_child_symbols",
    "get_outgoing_edges",
    "get_incoming_edges",
    "get_symbols_for_file",
    "get_repo_graph_stats",
    "CALLABLE_KINDS",
    "LOCAL_CALLABLE_KINDS",
    # Reference queries
    "list_reference_edges_for_target",
    "list_referenced_by",
    "list_references_from_symbol",
    "build_reference_stats",
    "get_reference_refresh_state",
    # Risk engine
    "analyze_symbol_risk",
    "analyze_target_set_risk",
    # Risk types
    "RiskTarget",
    "RiskFacts",
    "RiskResult",
    # Risk issue codes
    "ISSUE_STALE_CONTEXT",
    "ISSUE_LOW_CONFIDENCE_MATCH",
    "ISSUE_HIGH_REFERENCE_COUNT",
    "ISSUE_CROSS_FILE_IMPACT",
    "ISSUE_CROSS_MODULE_IMPACT",
    "ISSUE_PUBLIC_SURFACE_CHANGE",
    "ISSUE_INHERITANCE_RISK",
    "ISSUE_MULTI_FILE_CHANGE",
    "ISSUE_MULTI_MODULE_CHANGE",
    "ISSUE_REFERENCE_DATA_UNAVAILABLE",
    # Risk decisions
    "DECISION_SAFE_ENOUGH",
    "DECISION_REVIEW_REQUIRED",
    "DECISION_HIGH_RISK",
]
