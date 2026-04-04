"""MCP tool error helpers.

Provides structured error results for all MCP tools.
"""

# Error codes used by MCP tools
ERROR_INVALID_INPUT = "invalid_input"
ERROR_SYMBOL_NOT_FOUND = "symbol_not_found"
ERROR_AMBIGUOUS_SYMBOL = "ambiguous_symbol"
ERROR_REFERENCES_UNAVAILABLE = "references_unavailable"
ERROR_LSP_FAILURE = "lsp_failure"
ERROR_STALE_CONTEXT = "stale_context"
ERROR_INTERNAL_ERROR = "internal_error"


def error_result(code: str, message: str, details: dict | None = None) -> dict:
    """Build a structured error result following the shared result contract.

    Args:
        code: One of the ERROR_* constants.
        message: Human-readable error message.
        details: Optional dict with additional context.

    Returns:
        Dict with ok=false, error={code, message, details}, data=null.
    """
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
        "data": None,
    }


def success_result(data: dict) -> dict:
    """Build a structured success result following the shared result contract.

    Args:
        data: The success payload.

    Returns:
        Dict with ok=true, data={...}, error=null.
    """
    return {
        "ok": True,
        "data": data,
        "error": None,
    }
