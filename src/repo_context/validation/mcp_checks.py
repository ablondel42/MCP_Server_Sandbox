"""MCP contract validators.

Provides schema and payload validation for MCP tool outputs
to ensure payloads are validated as real machine contracts.
"""

from typing import Any

from repo_context.validation.contracts import (
    validate_required_fields,
)


def assert_tool_result_shape(tool_result: dict[str, Any]) -> dict:
    """Assert that MCP tool result has valid wrapper shape.

    Expected shape:
    {"ok": bool, "data": dict|None, "error": dict|None}

    Args:
        tool_result: MCP tool result dict.

    Returns:
        Dict with 'passed', 'is_success', 'errors'.
    """
    errors = []
    missing = validate_required_fields(tool_result, ["ok", "data", "error"])
    errors.extend(missing)

    ok = tool_result.get("ok")
    if ok is not None and not isinstance(ok, bool):
        errors.append(f"'ok' expected bool, got {type(ok).__name__}")

    is_success = ok is True

    return {
        "check": "tool_result_shape",
        "passed": len(errors) == 0,
        "is_success": is_success,
        "errors": errors,
    }


def assert_tool_error_shape(tool_result: dict[str, Any]) -> dict:
    """Assert that MCP tool error has valid shape.

    Expected error shape:
    {"code": str, "message": str, "details": dict|None}

    Args:
        tool_result: MCP tool result dict (with ok=False).

    Returns:
        Dict with 'passed', 'error_code', 'errors'.
    """
    errors = []

    if tool_result.get("ok") is not False:
        errors.append("Expected ok=False for error shape validation")

    error = tool_result.get("error")
    if error is None:
        errors.append("Missing 'error' field for failed result")
        return {
            "check": "tool_error_shape",
            "passed": False,
            "error_code": None,
            "errors": errors,
        }

    if not isinstance(error, dict):
        errors.append(f"'error' expected dict, got {type(error).__name__}")
        return {
            "check": "tool_error_shape",
            "passed": False,
            "error_code": None,
            "errors": errors,
        }

    missing = validate_required_fields(error, ["code", "message"])
    errors.extend(missing)

    error_code = error.get("code")
    if not isinstance(error_code, str):
        errors.append(f"error.code expected str, got {type(error_code).__name__}")

    error_message = error.get("message")
    if not isinstance(error_message, str):
        errors.append(f"error.message expected str, got {type(error_message).__name__}")

    return {
        "check": "tool_error_shape",
        "passed": len(errors) == 0,
        "error_code": error_code,
        "errors": errors,
    }


def assert_resolve_symbol_payload(tool_result: dict[str, Any]) -> dict:
    """Assert that resolve_symbol tool payload is valid.

    Args:
        tool_result: MCP tool result dict.

    Returns:
        Dict with 'passed', 'has_symbol', 'errors'.
    """
    errors = []

    # Check wrapper shape
    wrapper_check = assert_tool_result_shape(tool_result)
    errors.extend(wrapper_check.get("errors", []))

    if not wrapper_check["passed"]:
        return {
            "check": "resolve_symbol_payload",
            "passed": False,
            "has_symbol": False,
            "errors": errors,
        }

    data = tool_result.get("data", {})
    if not isinstance(data, dict):
        errors.append(f"'data' expected dict, got {type(data).__name__}")
        return {
            "check": "resolve_symbol_payload",
            "passed": False,
            "has_symbol": False,
            "errors": errors,
        }

    symbol = data.get("symbol", {})
    if not isinstance(symbol, dict):
        errors.append(f"'data.symbol' expected dict, got {type(symbol).__name__}")
    else:
        symbol_errors = validate_required_fields(
            symbol, ["id", "kind", "qualified_name"]
        )
        errors.extend(symbol_errors)

    return {
        "check": "resolve_symbol_payload",
        "passed": len(errors) == 0,
        "has_symbol": isinstance(symbol, dict) and "id" in symbol,
        "symbol_id": symbol.get("id"),
        "errors": errors,
    }


def assert_symbol_context_payload(tool_result: dict[str, Any]) -> dict:
    """Assert that symbol context tool payload is valid.

    Args:
        tool_result: MCP tool result dict.

    Returns:
        Dict with 'passed', 'has_context', 'errors'.
    """
    errors = []

    # Check wrapper shape
    wrapper_check = assert_tool_result_shape(tool_result)
    errors.extend(wrapper_check.get("errors", []))

    if not wrapper_check["passed"]:
        return {
            "check": "symbol_context_payload",
            "passed": False,
            "has_context": False,
            "errors": errors,
        }

    data = tool_result.get("data", {})
    if not isinstance(data, dict):
        errors.append(f"'data' expected dict, got {type(data).__name__}")
        return {
            "check": "symbol_context_payload",
            "passed": False,
            "has_context": False,
            "errors": errors,
        }

    context = data.get("context", {})
    if not isinstance(context, dict):
        errors.append(f"'data.context' expected dict, got {type(context).__name__}")
    else:
        context_errors = validate_required_fields(
            context,
            [
                "focus_symbol",
                "structural_parent",
                "structural_children",
                "lexical_parent",
                "lexical_children",
                "incoming_edges",
                "outgoing_edges",
            ],
        )
        errors.extend(context_errors)

    return {
        "check": "symbol_context_payload",
        "passed": len(errors) == 0,
        "has_context": isinstance(context, dict) and "focus_symbol" in context,
        "errors": errors,
    }


def assert_symbol_references_payload(tool_result: dict[str, Any]) -> dict:
    """Assert that symbol references tool payload is valid.

    Args:
        tool_result: MCP tool result dict.

    Returns:
        Dict with 'passed', 'has_references', 'errors'.
    """
    errors = []

    # Check wrapper shape
    wrapper_check = assert_tool_result_shape(tool_result)
    errors.extend(wrapper_check.get("errors", []))

    if not wrapper_check["passed"]:
        return {
            "check": "symbol_references_payload",
            "passed": False,
            "has_references": False,
            "errors": errors,
        }

    data = tool_result.get("data", {})
    if not isinstance(data, dict):
        errors.append(f"'data' expected dict, got {type(data).__name__}")
        return {
            "check": "symbol_references_payload",
            "passed": False,
            "has_references": False,
            "errors": errors,
        }

    missing = validate_required_fields(data, ["references", "reference_summary"])
    errors.extend(missing)

    refs = data.get("references", [])
    if not isinstance(refs, list):
        errors.append(f"'references' expected list, got {type(refs).__name__}")

    summary = data.get("reference_summary", {})
    if not isinstance(summary, dict):
        errors.append(f"'reference_summary' expected dict, got {type(summary).__name__}")

    return {
        "check": "symbol_references_payload",
        "passed": len(errors) == 0,
        "has_references": isinstance(refs, list),
        "reference_count": len(refs) if isinstance(refs, list) else 0,
        "errors": errors,
    }


def assert_risk_payload(tool_result: dict[str, Any]) -> dict:
    """Assert that risk analysis tool payload is valid.

    Args:
        tool_result: MCP tool result dict.

    Returns:
        Dict with 'passed', 'has_risk', 'errors'.
    """
    errors = []

    # Check wrapper shape
    wrapper_check = assert_tool_result_shape(tool_result)
    errors.extend(wrapper_check.get("errors", []))

    if not wrapper_check["passed"]:
        return {
            "check": "risk_payload",
            "passed": False,
            "has_risk": False,
            "errors": errors,
        }

    data = tool_result.get("data", {})
    if not isinstance(data, dict):
        errors.append(f"'data' expected dict, got {type(data).__name__}")
        return {
            "check": "risk_payload",
            "passed": False,
            "has_risk": False,
            "errors": errors,
        }

    risk = data.get("risk", {})
    if not isinstance(risk, dict):
        errors.append(f"'data.risk' expected dict, got {type(risk).__name__}")
    else:
        risk_errors = validate_required_fields(
            risk, ["risk_score", "decision", "issues", "facts"]
        )
        errors.extend(risk_errors)

    return {
        "check": "risk_payload",
        "passed": len(errors) == 0,
        "has_risk": isinstance(risk, dict) and "risk_score" in risk,
        "risk_score": risk.get("risk_score"),
        "decision": risk.get("decision"),
        "errors": errors,
    }


def assert_mcp_payload_is_agent_usable(
    tool_result: dict[str, Any],
    tool_name: str = "",
) -> dict:
    """Assert that MCP payload is agent-usable overall.

    Checks:
    - Wrapper shape is valid
    - Success results have valid data
    - Error results have valid error shape
    - Payload shape matches expected contract

    Args:
        tool_result: MCP tool result dict.
        tool_name: Name of the tool for context.

    Returns:
        Dict with 'passed', 'sub_checks', 'errors'.
    """
    errors = []
    context = f"Tool '{tool_name}'" if tool_name else ""

    # Check wrapper shape
    wrapper_check = assert_tool_result_shape(tool_result)
    errors.extend(wrapper_check.get("errors", []))

    if not wrapper_check["passed"]:
        return {
            "check": "mcp_payload_is_agent_usable",
            "passed": False,
            "sub_checks": {"wrapper_shape": wrapper_check},
            "errors": errors,
        }

    # Check error shape if failed
    if not tool_result.get("ok"):
        error_check = assert_tool_error_shape(tool_result)
        errors.extend(error_check.get("errors", []))
        return {
            "check": "mcp_payload_is_agent_usable",
            "passed": len(errors) == 0,
            "sub_checks": {
                "wrapper_shape": wrapper_check,
                "error_shape": error_check,
            },
            "errors": errors,
        }

    # Success: validate data is present
    data = tool_result.get("data")
    if data is None:
        errors.append(f"{context}: Success result has null data")

    return {
        "check": "mcp_payload_is_agent_usable",
        "passed": len(errors) == 0,
        "sub_checks": {"wrapper_shape": wrapper_check},
        "is_success": wrapper_check["is_success"],
        "has_data": data is not None,
        "errors": errors,
    }
