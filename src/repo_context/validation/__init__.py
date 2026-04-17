"""Validation package for end-to-end workflow verification.

Provides fixture-driven validation runners, contract checkers,
and shape validators for graph, context, references, risk, and MCP outputs.
"""

__all__ = [
    "run_full_workflow_validation",
    "run_symbol_workflow_validation",
    "run_mcp_workflow_validation",
    "run_watch_workflow_validation",
    "ValidationResult",
]


from repo_context.validation.workflow import (
    run_full_workflow_validation,
    run_symbol_workflow_validation,
    run_mcp_workflow_validation,
    run_watch_workflow_validation,
    ValidationResult,
)
