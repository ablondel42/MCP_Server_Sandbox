"""Risk scoring and decision logic.

Computes numeric risk score from issue codes and determines final decision.
"""

from repo_context.graph.risk_types import RiskFacts
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

# Decision constants
DECISION_SAFE_ENOUGH = "safe_enough"
DECISION_REVIEW_REQUIRED = "review_required"
DECISION_HIGH_RISK = "high_risk"

# Issue weights
ISSUE_WEIGHTS = {
    ISSUE_STALE_CONTEXT: 20,
    ISSUE_LOW_CONFIDENCE_MATCH: 20,
    ISSUE_HIGH_REFERENCE_COUNT: 20,
    ISSUE_CROSS_FILE_IMPACT: 10,
    ISSUE_CROSS_MODULE_IMPACT: 15,
    ISSUE_PUBLIC_SURFACE_CHANGE: 15,
    ISSUE_INHERITANCE_RISK: 10,
    ISSUE_MULTI_FILE_CHANGE: 10,
    ISSUE_MULTI_MODULE_CHANGE: 15,
    ISSUE_REFERENCE_DATA_UNAVAILABLE: 15,
}

# Local-scope mitigation (applied if touches_local_scope_only and no public_surface_change)
LOCAL_SCOPE_MITIGATION = -10


def score_risk(issues: list[str], facts: RiskFacts) -> int:
    """Compute risk score from issue codes.

    Args:
        issues: List of triggered issue codes.
        facts: Risk facts (used for local-scope mitigation).

    Returns:
        Risk score clamped to 0-100 range.
    """
    # Sum weights of triggered issues
    score = sum(ISSUE_WEIGHTS.get(issue, 0) for issue in issues)

    # Apply local-scope mitigation if applicable
    if facts.touches_local_scope_only and not facts.touches_public_surface:
        score += LOCAL_SCOPE_MITIGATION

    # Clamp to 0-100
    return max(0, min(100, score))


def decide_risk(issues: list[str], facts: RiskFacts, score: int) -> str:
    """Determine final risk decision.

    Base thresholds:
    - 0-29: safe_enough
    - 30-69: review_required
    - 70-100: high_risk

    Override rules:
    - stale_context → at least review_required
    - low_confidence_match + another issue → at least review_required
    - reference_data_unavailable + (public_surface OR cross_module OR inheritance) → at least review_required

    Args:
        issues: List of triggered issue codes.
        facts: Risk facts.
        score: Computed risk score.

    Returns:
        Decision string (safe_enough, review_required, high_risk).
    """
    # Base decision from score
    if score >= 70:
        decision = DECISION_HIGH_RISK
    elif score >= 30:
        decision = DECISION_REVIEW_REQUIRED
    else:
        decision = DECISION_SAFE_ENOUGH

    # Override: stale_context → at least review_required
    if ISSUE_STALE_CONTEXT in issues:
        if decision == DECISION_SAFE_ENOUGH:
            decision = DECISION_REVIEW_REQUIRED

    # Override: low_confidence_match + another issue → at least review_required
    if ISSUE_LOW_CONFIDENCE_MATCH in issues:
        other_issues = [i for i in issues if i != ISSUE_LOW_CONFIDENCE_MATCH]
        if other_issues:
            if decision == DECISION_SAFE_ENOUGH:
                decision = DECISION_REVIEW_REQUIRED

    # Override: reference_data_unavailable + significant issue → at least review_required
    if ISSUE_REFERENCE_DATA_UNAVAILABLE in issues:
        significant_issues = {
            ISSUE_PUBLIC_SURFACE_CHANGE,
            ISSUE_CROSS_MODULE_IMPACT,
            ISSUE_INHERITANCE_RISK,
        }
        if any(issue in significant_issues for issue in issues):
            if decision == DECISION_SAFE_ENOUGH:
                decision = DECISION_REVIEW_REQUIRED

    return decision
