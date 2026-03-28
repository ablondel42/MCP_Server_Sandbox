"""Summary builders for symbol context."""

from repo_context.models import SymbolContext
from repo_context.context.helpers import has_placeholder_targets


LOCAL_CALLABLE_KINDS = {"local_function", "local_async_function"}


def _is_local_declaration(focus_symbol: dict) -> bool:
    """Check if symbol is a local declaration.
    
    Args:
        focus_symbol: Focus symbol dictionary.
        
    Returns:
        True if symbol is a local function or class with scope="function".
    """
    kind = focus_symbol.get("kind", "")
    scope = focus_symbol.get("scope", "")
    
    # Local functions
    if kind in LOCAL_CALLABLE_KINDS:
        return True
    
    # Local classes (scope = "function")
    if kind == "class" and scope == "function":
        return True
    
    return False


def build_structural_summary(context: SymbolContext) -> dict:
    """Build a compact structural summary from context.
    
    Args:
        context: Symbol context.
        
    Returns:
        Dictionary with structural summary fields.
    """
    focus = context.focus_symbol
    
    return {
        "has_structural_parent": context.structural_parent is not None,
        "structural_child_count": len(context.structural_children),
        "has_lexical_parent": context.lexical_parent is not None,
        "lexical_child_count": len(context.lexical_children),
        "incoming_edge_count": len(context.incoming_edges),
        "outgoing_edge_count": len(context.outgoing_edges),
        "same_file_sibling_count": len(context.file_siblings),
        "scope": focus.get("scope"),
        "is_local_declaration": _is_local_declaration(focus),
        "is_nested_declaration": focus.get("lexical_parent_id") is not None,
    }


def build_confidence(context: SymbolContext) -> dict:
    """Build confidence metadata from context.
    
    Args:
        context: Symbol context.
        
    Returns:
        Dictionary with confidence fields.
    """
    focus = context.focus_symbol
    
    # Collect edge confidences
    all_edges = context.incoming_edges + context.outgoing_edges
    edge_confidences = [e.get("confidence", 1.0) for e in all_edges]
    
    return {
        "focus_symbol_confidence": focus.get("confidence", 1.0),
        "edge_confidence_min": min(edge_confidences) if edge_confidences else 1.0,
        "edge_confidence_max": max(edge_confidences) if edge_confidences else 1.0,
        "contains_placeholder_targets": has_placeholder_targets(context),
        "graph_only": True,
    }
