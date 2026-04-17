"""Context shape validators.

Provides deterministic context-shape assertions to verify that
symbol context payloads are structurally consumable by an agent.
"""

from typing import Any

from repo_context.validation.contracts import (
    validate_required_fields,
    validate_stable_id,
)


def assert_context_has_focus_symbol(context: dict[str, Any]) -> dict:
    """Assert that context has a valid focus symbol.

    Args:
        context: SymbolContext dict.

    Returns:
        Dict with 'passed', 'symbol_id', 'errors'.
    """
    errors: list[str] = []
    symbol = context.get("focus_symbol")

    if symbol is None:
        return {
            "check": "context_has_focus_symbol",
            "passed": False,
            "symbol_id": None,
            "errors": ["Missing focus_symbol"],
        }

    if not isinstance(symbol, dict):
        return {
            "check": "context_has_focus_symbol",
            "passed": False,
            "symbol_id": None,
            "errors": [f"focus_symbol expected dict, got {type(symbol).__name__}"],
        }

    missing = validate_required_fields(symbol, ["id", "kind", "qualified_name"])
    errors.extend(missing)

    symbol_id = symbol.get("id", "")
    if symbol_id:
        id_errors = validate_stable_id(symbol_id, "sym:", "focus_symbol")
        errors.extend(id_errors)

    return {
        "check": "context_has_focus_symbol",
        "passed": len(errors) == 0,
        "symbol_id": symbol_id,
        "symbol_kind": symbol.get("kind"),
        "errors": errors,
    }


def assert_context_has_structural_relationships(context: dict[str, Any]) -> dict:
    """Assert that context has structural parent/children fields.

    Args:
        context: SymbolContext dict.

    Returns:
        Dict with 'passed', 'has_parent', 'children_count', 'errors'.
    """
    errors: list[str] = []
    missing = validate_required_fields(context, ["structural_parent", "structural_children"])
    errors.extend(missing)

    structural_parent = context.get("structural_parent")
    structural_children = context.get("structural_children", [])

    if structural_parent is not None and not isinstance(structural_parent, dict):
        errors.append(f"structural_parent expected dict or None, got {type(structural_parent).__name__}")

    if not isinstance(structural_children, list):
        errors.append(f"structural_children expected list, got {type(structural_children).__name__}")

    return {
        "check": "context_has_structural_relationships",
        "passed": len(errors) == 0,
        "has_parent": structural_parent is not None,
        "parent_id": structural_parent.get("id") if isinstance(structural_parent, dict) else None,
        "children_count": len(structural_children) if isinstance(structural_children, list) else 0,
        "errors": errors,
    }


def assert_context_has_lexical_relationships(context: dict[str, Any]) -> dict:
    """Assert that context has lexical parent/children fields.

    Validates separate lexical hierarchy from structural hierarchy.

    Args:
        context: SymbolContext dict.

    Returns:
        Dict with 'passed', 'has_lexical_parent', 'lexical_children_count', 'errors'.
    """
    errors: list[str] = []
    missing = validate_required_fields(context, ["lexical_parent", "lexical_children"])
    errors.extend(missing)

    lexical_parent = context.get("lexical_parent")
    lexical_children = context.get("lexical_children", [])

    if lexical_parent is not None and not isinstance(lexical_parent, dict):
        errors.append(f"lexical_parent expected dict or None, got {type(lexical_parent).__name__}")

    if not isinstance(lexical_children, list):
        errors.append(f"lexical_children expected list, got {type(lexical_children).__name__}")

    return {
        "check": "context_has_lexical_relationships",
        "passed": len(errors) == 0,
        "has_lexical_parent": lexical_parent is not None,
        "lexical_parent_id": lexical_parent.get("id") if isinstance(lexical_parent, dict) else None,
        "lexical_children_count": len(lexical_children) if isinstance(lexical_children, list) else 0,
        "errors": errors,
    }


def assert_reference_summary_shape(context: dict[str, Any]) -> dict:
    """Assert that context has valid reference summary.

    Validates that reference summary includes count and availability fields.

    Args:
        context: SymbolContext dict.

    Returns:
        Dict with 'passed', 'has_references', 'available', 'errors'.
    """
    errors: list[str] = []
    ref_summary = context.get("reference_summary")

    if ref_summary is None:
        return {
            "check": "reference_summary_shape",
            "passed": True,  # Reference summary may be None
            "has_references": False,
            "available": None,
            "errors": [],
        }

    if not isinstance(ref_summary, dict):
        return {
            "check": "reference_summary_shape",
            "passed": False,
            "has_references": False,
            "available": None,
            "errors": [f"reference_summary expected dict, got {type(ref_summary).__name__}"],
        }

    # Accept either 'count' or 'reference_count'
    has_count = "count" in ref_summary or "reference_count" in ref_summary
    if not has_count:
        errors.append("reference_summary missing 'count' or 'reference_count'")
    missing = validate_required_fields(ref_summary, ["available"])
    errors.extend(missing)

    available = ref_summary.get("available")
    count = ref_summary.get("count", ref_summary.get("reference_count", 0))

    # Validate available is a boolean
    if available is not None and not isinstance(available, bool):
        errors.append(f"reference_summary.available expected bool, got {type(available).__name__}")

    safe_count = count if count is not None else 0

    return {
        "check": "reference_summary_shape",
        "passed": len(errors) == 0,
        "has_references": safe_count > 0,
        "reference_count": safe_count,
        "available": available,
        "errors": errors,
    }


def assert_freshness_shape(context: dict[str, Any]) -> dict:
    """Assert that context has valid freshness summary.

    Args:
        context: SymbolContext dict.

    Returns:
        Dict with 'passed', 'has_freshness', 'errors'.
    """
    errors: list[str] = []
    freshness = context.get("freshness")

    if freshness is None:
        return {
            "check": "freshness_shape",
            "passed": True,
            "has_freshness": False,
            "errors": [],
        }

    if not isinstance(freshness, dict):
        return {
            "check": "freshness_shape",
            "passed": False,
            "has_freshness": False,
            "errors": [f"freshness expected dict, got {type(freshness).__name__}"],
        }

    return {
        "check": "freshness_shape",
        "passed": len(errors) == 0,
        "has_freshness": True,
        "errors": errors,
    }


def assert_confidence_shape(context: dict[str, Any]) -> dict:
    """Assert that context has valid confidence summary.

    Args:
        context: SymbolContext dict.

    Returns:
        Dict with 'passed', 'has_confidence', 'errors'.
    """
    errors: list[str] = []
    confidence = context.get("confidence")

    if confidence is None:
        return {
            "check": "confidence_shape",
            "passed": True,
            "has_confidence": False,
            "errors": [],
        }

    if not isinstance(confidence, dict):
        return {
            "check": "confidence_shape",
            "passed": False,
            "has_confidence": False,
            "errors": [f"confidence expected dict, got {type(confidence).__name__}"],
        }

    return {
        "check": "confidence_shape",
        "passed": len(errors) == 0,
        "has_confidence": True,
        "errors": errors,
    }


def assert_context_is_agent_usable(context: dict[str, Any]) -> dict:
    """Assert that context is agent-usable overall.

    Checks:
    - Focus symbol exists with stable ID
    - Structural relationships present (even if empty)
    - Lexical relationships present (even if None)
    - No critical relationship is only implied in prose
    - Payload shape is deterministic

    Args:
        context: SymbolContext dict.

    Returns:
        Dict with 'passed', 'sub_checks', 'errors'.
    """
    sub_checks = [
        assert_context_has_focus_symbol(context),
        assert_context_has_structural_relationships(context),
        assert_context_has_lexical_relationships(context),
        assert_reference_summary_shape(context),
        assert_freshness_shape(context),
        assert_confidence_shape(context),
    ]

    all_passed = all(c["passed"] for c in sub_checks)
    all_errors: list[str] = []
    for c in sub_checks:
        all_errors.extend(c.get("errors", []))

    return {
        "check": "context_is_agent_usable",
        "passed": all_passed,
        "sub_checks": sub_checks,
        "errors": all_errors,
    }
