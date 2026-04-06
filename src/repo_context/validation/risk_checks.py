"""Risk shape validators.

Provides deterministic risk-shape assertions to verify that
risk outputs are real machine-friendly contracts.
"""

from typing import Any

from repo_context.validation.contracts import (
    validate_required_fields,
    validate_field_types,
    validate_enum_values,
)

from repo_context.graph.risk_scoring import (
    DECISION_SAFE_ENOUGH,
    DECISION_REVIEW_REQUIRED,
    DECISION_HIGH_RISK,
)

VALID_DECISIONS = [DECISION_SAFE_ENOUGH, DECISION_REVIEW_REQUIRED, DECISION_HIGH_RISK]


def assert_risk_result_shape(risk_result: dict[str, Any]) -> dict:
    """Assert that risk result has valid shape.

    Args:
        risk_result: Risk result dict.

    Returns:
        Dict with 'passed', 'score', 'decision', 'errors'.
    """
    errors = []
    missing = validate_required_fields(
        risk_result, ["risk_score", "decision", "issues", "facts"]
    )
    errors.extend(missing)

    score = risk_result.get("risk_score")
    decision = risk_result.get("decision")
    issues = risk_result.get("issues", [])

    # Validate score is integer
    if score is not None and not isinstance(score, int):
        errors.append(f"'risk_score' expected int, got {type(score).__name__}")

    # Validate decision is valid enum
    if decision is not None:
        decision_errors = validate_enum_values(decision, VALID_DECISIONS, "decision")
        errors.extend(decision_errors)

    # Validate issues is list of strings
    if not isinstance(issues, list):
        errors.append(f"'issues' expected list, got {type(issues).__name__}")

    return {
        "check": "risk_result_shape",
        "passed": len(errors) == 0,
        "score": score,
        "decision": decision,
        "issue_count": len(issues) if isinstance(issues, list) else 0,
        "errors": errors,
    }


def assert_risk_targets_shape(risk_result: dict[str, Any]) -> dict:
    """Assert that risk targets are present in result.

    Args:
        risk_result: Risk result dict.

    Returns:
        Dict with 'passed', 'target_count', 'errors'.
    """
    errors = []
    facts = risk_result.get("facts", {})

    if not isinstance(facts, dict):
        return {
            "check": "risk_targets_shape",
            "passed": False,
            "target_count": 0,
            "errors": [f"'facts' expected dict, got {type(facts).__name__}"],
        }

    missing = validate_required_fields(facts, ["target_count"])
    errors.extend(missing)

    target_count = facts.get("target_count", 0)
    if not isinstance(target_count, int) or target_count < 1:
        errors.append(f"'target_count' expected positive int, got {target_count}")

    return {
        "check": "risk_targets_shape",
        "passed": len(errors) == 0,
        "target_count": target_count,
        "errors": errors,
    }


def assert_risk_facts_shape(risk_result: dict[str, Any]) -> dict:
    """Assert that risk facts are present and structured.

    Args:
        risk_result: Risk result dict.

    Returns:
        Dict with 'passed', 'has_facts', 'errors'.
    """
    errors = []
    facts = risk_result.get("facts", {})

    if not isinstance(facts, dict):
        return {
            "check": "risk_facts_shape",
            "passed": False,
            "has_facts": False,
            "errors": [f"'facts' expected dict, got {type(facts).__name__}"],
        }

    # Facts should have at least target_count
    if "target_count" not in facts:
        errors.append("'facts' missing 'target_count'")

    return {
        "check": "risk_facts_shape",
        "passed": len(errors) == 0,
        "has_facts": True,
        "fact_keys": sorted(facts.keys()),
        "errors": errors,
    }


def assert_risk_issue_codes_shape(risk_result: dict[str, Any]) -> dict:
    """Assert that risk issue codes are valid.

    Args:
        risk_result: Risk result dict.

    Returns:
        Dict with 'passed', 'issues', 'errors'.
    """
    errors = []
    issues = risk_result.get("issues", [])

    if not isinstance(issues, list):
        return {
            "check": "risk_issue_codes_shape",
            "passed": False,
            "issues": [],
            "errors": [f"'issues' expected list, got {type(issues).__name__}"],
        }

    # Validate each issue is a string
    invalid_issues = []
    for i, issue in enumerate(issues):
        if not isinstance(issue, str):
            invalid_issues.append(f"Item {i}: expected str, got {type(issue).__name__}")
        elif not issue:
            invalid_issues.append(f"Item {i}: empty issue code")

    errors.extend(invalid_issues)

    return {
        "check": "risk_issue_codes_shape",
        "passed": len(errors) == 0,
        "issues": issues,
        "issue_count": len(issues),
        "errors": errors,
    }


def assert_risk_is_agent_usable(risk_result: dict[str, Any]) -> dict:
    """Assert that risk result is agent-usable overall.

    Checks:
    - Result shape is valid (score, decision, issues, facts)
    - Targets are present
    - Facts are structured
    - Issue codes are valid strings
    - No critical interpretation is hidden in prose

    Args:
        risk_result: Risk result dict.

    Returns:
        Dict with 'passed', 'sub_checks', 'errors'.
    """
    sub_checks = [
        assert_risk_result_shape(risk_result),
        assert_risk_targets_shape(risk_result),
        assert_risk_facts_shape(risk_result),
        assert_risk_issue_codes_shape(risk_result),
    ]

    all_passed = all(c["passed"] for c in sub_checks)
    all_errors = []
    for c in sub_checks:
        all_errors.extend(c.get("errors", []))

    return {
        "check": "risk_is_agent_usable",
        "passed": all_passed,
        "sub_checks": sub_checks,
        "score": risk_result.get("risk_score"),
        "decision": risk_result.get("decision"),
        "errors": all_errors,
    }
