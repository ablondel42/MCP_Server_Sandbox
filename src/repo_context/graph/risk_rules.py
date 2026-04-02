"""Risk issue detection rules.

Detects issue codes from extracted risk facts.
Each issue code represents a specific risk pattern.
"""

from repo_context.graph.risk_types import RiskFacts

# All allowed issue codes
ISSUE_STALE_CONTEXT = "stale_context"
ISSUE_LOW_CONFIDENCE_MATCH = "low_confidence_match"
ISSUE_HIGH_REFERENCE_COUNT = "high_reference_count"
ISSUE_MODERATE_REFERENCE_COUNT = "moderate_reference_count"
ISSUE_CROSS_FILE_IMPACT = "cross_file_impact"
ISSUE_CROSS_MODULE_IMPACT = "cross_module_impact"
ISSUE_PUBLIC_SURFACE_CHANGE = "public_surface_change"
ISSUE_INHERITANCE_RISK = "inheritance_risk"
ISSUE_MULTI_FILE_CHANGE = "multi_file_change"
ISSUE_MULTI_MODULE_CHANGE = "multi_module_change"
ISSUE_REFERENCE_DATA_UNAVAILABLE = "reference_data_unavailable"

ALL_ISSUE_CODES = [
    ISSUE_STALE_CONTEXT,
    ISSUE_LOW_CONFIDENCE_MATCH,
    ISSUE_HIGH_REFERENCE_COUNT,
    ISSUE_MODERATE_REFERENCE_COUNT,
    ISSUE_CROSS_FILE_IMPACT,
    ISSUE_CROSS_MODULE_IMPACT,
    ISSUE_PUBLIC_SURFACE_CHANGE,
    ISSUE_INHERITANCE_RISK,
    ISSUE_MULTI_FILE_CHANGE,
    ISSUE_MULTI_MODULE_CHANGE,
    ISSUE_REFERENCE_DATA_UNAVAILABLE,
]


def detect_risk_issues(facts: RiskFacts) -> list[str]:
    """Detect risk issues from extracted facts.

    Args:
        facts: Populated RiskFacts object.

    Returns:
        List of triggered issue codes in deterministic order.
    """
    issues = []

    # stale_context: stale_symbols is not empty
    if facts.stale_symbols:
        issues.append(ISSUE_STALE_CONTEXT)

    # low_confidence_match: low_confidence_symbols or low_confidence_edges not empty
    if facts.low_confidence_symbols or facts.low_confidence_edges:
        issues.append(ISSUE_LOW_CONFIDENCE_MATCH)

    # Reference count issues - scaled by actual count
    # Check for heavy usage first (15+), then moderate (5+)
    has_heavy_refs = False
    has_moderate_refs = False
    
    for symbol_id, count in facts.reference_counts.items():
        if count >= 15 and facts.reference_availability.get(symbol_id, False):
            has_heavy_refs = True
            break
        elif count >= 5 and facts.reference_availability.get(symbol_id, False):
            has_moderate_refs = True
    
    if has_heavy_refs:
        issues.append(ISSUE_HIGH_REFERENCE_COUNT)
    elif has_moderate_refs:
        issues.append(ISSUE_MODERATE_REFERENCE_COUNT)

    # cross_file_impact: facts.cross_file_impact is True
    if facts.cross_file_impact:
        issues.append(ISSUE_CROSS_FILE_IMPACT)

    # cross_module_impact: facts.cross_module_impact is True
    if facts.cross_module_impact:
        issues.append(ISSUE_CROSS_MODULE_IMPACT)

    # public_surface_change: facts.touches_public_surface is True
    if facts.touches_public_surface:
        issues.append(ISSUE_PUBLIC_SURFACE_CHANGE)

    # inheritance_risk: facts.inheritance_involved is True
    if facts.inheritance_involved:
        issues.append(ISSUE_INHERITANCE_RISK)

    # multi_file_change: facts.target_spans_multiple_files is True
    if facts.target_spans_multiple_files:
        issues.append(ISSUE_MULTI_FILE_CHANGE)

    # multi_module_change: facts.target_spans_multiple_modules is True
    if facts.target_spans_multiple_modules:
        issues.append(ISSUE_MULTI_MODULE_CHANGE)

    # reference_data_unavailable: any target has availability=False
    if not all(facts.reference_availability.values()) and facts.reference_availability:
        issues.append(ISSUE_REFERENCE_DATA_UNAVAILABLE)

    return issues
