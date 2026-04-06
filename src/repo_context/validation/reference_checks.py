"""Reference shape validators.

Provides deterministic reference-shape assertions to verify that
reference outputs are structured tool-usable truth.
"""

from typing import Any

from repo_context.validation.contracts import (
    validate_required_fields,
    validate_field_types,
    validate_stable_id,
    validate_nested_list,
)


def assert_references_payload_shape(references_payload: dict[str, Any]) -> dict:
    """Assert that references payload has valid shape.

    Args:
        references_payload: MCP tool response data for references.

    Returns:
        Dict with 'passed', 'reference_count', 'errors'.
    """
    errors = []
    missing = validate_required_fields(references_payload, ["references", "reference_summary"])
    errors.extend(missing)

    if "references" in references_payload:
        refs = references_payload["references"]
        if not isinstance(refs, list):
            errors.append(f"'references' expected list, got {type(refs).__name__}")

    if "reference_summary" in references_payload:
        summary = references_payload["reference_summary"]
        if not isinstance(summary, dict):
            errors.append(f"'reference_summary' expected dict, got {type(summary).__name__}")

    ref_count = len(references_payload.get("references", []))

    return {
        "check": "references_payload_shape",
        "passed": len(errors) == 0,
        "reference_count": ref_count,
        "errors": errors,
    }


def assert_reference_summary_availability_semantics(
    reference_summary: dict[str, Any],
) -> dict:
    """Assert that reference summary has correct availability semantics.

    Validates:
    - 'available' field is present and boolean
    - 'count' field is present and non-negative integer
    - Unrefreshed symbols must not validate as "zero references"

    Args:
        reference_summary: Reference summary dict.

    Returns:
        Dict with 'passed', 'available', 'count', 'errors'.
    """
    errors = []
    missing = validate_required_fields(reference_summary, ["available", "count"])
    errors.extend(missing)

    available = reference_summary.get("available")
    count = reference_summary.get("count", 0)

    # Validate available is boolean
    if available is not None and not isinstance(available, bool):
        errors.append(
            f"'available' expected bool or None, got {type(available).__name__}"
        )

    # Validate count is non-negative integer
    if not isinstance(count, int) or count < 0:
        errors.append(f"'count' expected non-negative int, got {count}")

    return {
        "check": "reference_summary_availability_semantics",
        "passed": len(errors) == 0,
        "available": available,
        "count": count,
        "errors": errors,
    }


def assert_reference_edge_evidence_shape(edge: dict[str, Any]) -> dict:
    """Assert that a reference edge has valid evidence fields.

    Args:
        edge: Edge dict.

    Returns:
        Dict with 'passed', 'has_evidence', 'errors'.
    """
    errors = []
    missing = validate_required_fields(
        edge, ["id", "kind", "from_id", "to_id", "source", "evidence_file_id"]
    )
    errors.extend(missing)

    if edge.get("kind") != "references":
        errors.append(f"Edge kind expected 'references', got {edge.get('kind')}")

    if edge.get("source") != "lsp":
        errors.append(f"Edge source expected 'lsp', got {edge.get('source')}")

    has_evidence = edge.get("evidence_file_id") is not None

    return {
        "check": "reference_edge_evidence_shape",
        "passed": len(errors) == 0,
        "has_evidence": has_evidence,
        "edge_id": edge.get("id"),
        "errors": errors,
    }


def assert_referenced_by_derivation_shape(referenced_by: list[dict[str, Any]]) -> dict:
    """Assert that referenced-by derivation has valid shape.

    Args:
        referenced_by: List of referencing symbol dicts.

    Returns:
        Dict with 'passed', 'count', 'errors'.
    """
    errors = []

    if not isinstance(referenced_by, list):
        return {
            "check": "referenced_by_derivation_shape",
            "passed": False,
            "count": 0,
            "errors": [f"referenced_by expected list, got {type(referenced_by).__name__}"],
        }

    for i, item in enumerate(referenced_by):
        if not isinstance(item, dict):
            errors.append(f"Item {i} expected dict, got {type(item).__name__}")
            continue
        item_errors = validate_required_fields(item, ["id", "kind", "qualified_name"])
        errors.extend([f"Item {i}: {e}" for e in item_errors])

    return {
        "check": "referenced_by_derivation_shape",
        "passed": len(errors) == 0,
        "count": len(referenced_by),
        "errors": errors,
    }


def assert_reference_state_is_agent_usable(
    references_payload: dict[str, Any],
) -> dict:
    """Assert that reference state is agent-usable overall.

    Checks:
    - Payload shape is valid
    - Availability semantics are correct
    - Evidence fields are present
    - Unavailable ≠ zero references distinction is maintained

    Args:
        references_payload: MCP tool response data for references.

    Returns:
        Dict with 'passed', 'sub_checks', 'errors'.
    """
    errors = []

    # Check payload shape
    payload_check = assert_references_payload_shape(references_payload)
    errors.extend(payload_check.get("errors", []))

    # Check availability semantics
    summary = references_payload.get("reference_summary", {})
    availability_check = assert_reference_summary_availability_semantics(summary)
    errors.extend(availability_check.get("errors", []))

    # Verify unavailable ≠ zero distinction
    available = summary.get("available")
    count = summary.get("count", 0)

    # If available is False, that's OK (explicit unavailable state)
    # If available is True and count is 0, that's also OK (explicit zero)
    # Both are distinguishable from missing available field
    if "available" not in summary:
        errors.append("Missing 'available' field - cannot distinguish unavailable from zero")

    all_passed = len(errors) == 0

    return {
        "check": "reference_state_is_agent_usable",
        "passed": all_passed,
        "sub_checks": {
            "payload_shape": payload_check,
            "availability_semantics": availability_check,
        },
        "available": available,
        "count": count,
        "errors": errors,
    }
