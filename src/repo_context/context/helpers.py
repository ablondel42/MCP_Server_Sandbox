"""Shared helper functions for context layer."""

from repo_context.models import SymbolContext


PLACEHOLDER_PREFIXES = ("external_or_unresolved:", "unresolved_base:")


def has_placeholder_targets(context: SymbolContext) -> bool:
    """Check if any edge has placeholder target IDs.
    
    Args:
        context: Symbol context to check.
        
    Returns:
        True if any edge endpoint contains placeholder prefix.
    """
    for edge in context.incoming_edges + context.outgoing_edges:
        from_id = edge.get("from_id", "")
        to_id = edge.get("to_id", "")
        for prefix in PLACEHOLDER_PREFIXES:
            if from_id.startswith(prefix) or to_id.startswith(prefix):
                return True
    return False
