"""Freshness metadata for symbol context."""


from repo_context.models import SymbolContext


def build_freshness(context: SymbolContext, focus_node: dict) -> dict:
    """Build freshness metadata from stored graph state.
    
    Args:
        context: Symbol context.
        focus_node: Original focus node from storage (for last_indexed_at).
        
    Returns:
        Dictionary with freshness fields.
    """
    # Get latest edge timestamp if edges exist
    
    # Note: edges don't have last_indexed_at exposed in adapted form
    # We use the focus node's timestamp as the primary freshness indicator
    edge_snapshot_timestamp = None
    
    return {
        "node_last_indexed_at": focus_node.get("last_indexed_at"),
        "edge_snapshot_last_indexed_at": edge_snapshot_timestamp,
        "has_incoming_edges": len(context.incoming_edges) > 0,
        "has_outgoing_edges": len(context.outgoing_edges) > 0,
        "context_source": "graph_only",
    }
