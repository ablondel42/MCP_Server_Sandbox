"""Context builders for assembling symbol-centered graph views."""

import sqlite3

from repo_context.models import SymbolContext
from repo_context.graph import (
    get_symbol,
    get_parent_symbol,
    get_child_symbols,
    get_lexical_parent_symbol,
    get_lexical_child_symbols,
    get_outgoing_edges,
    get_incoming_edges,
    get_symbols_for_file,
    build_reference_stats,
)
from repo_context.context.summaries import build_structural_summary, build_confidence
from repo_context.context.freshness import build_freshness


def adapt_node_to_symbol(node: dict) -> dict:
    """Adapt a stored node to a context symbol payload.
    
    Args:
        node: Node dictionary from storage.
        
    Returns:
        Symbol dictionary with required context fields.
    """
    return {
        "id": node["id"],
        "repo_id": node["repo_id"],
        "file_id": node["file_id"],
        "kind": node["kind"],
        "name": node["name"],
        "qualified_name": node["qualified_name"],
        "parent_id": node.get("parent_id"),
        "scope": node.get("scope"),
        "lexical_parent_id": node.get("lexical_parent_id"),
        "visibility_hint": node.get("visibility_hint"),
        "uri": node["uri"],
        "range": node.get("range_json"),
        "selection_range": node.get("selection_range_json"),
        "confidence": node.get("confidence", 1.0),
    }


def adapt_edge_to_context_edge(edge: dict) -> dict:
    """Adapt a stored edge to a context edge payload.
    
    Args:
        edge: Edge dictionary from storage.
        
    Returns:
        Edge dictionary with required context fields.
    """
    return {
        "id": edge["id"],
        "kind": edge["kind"],
        "from_id": edge["from_id"],
        "to_id": edge["to_id"],
        "evidence_file_id": edge.get("evidence_file_id"),
        "evidence_uri": edge.get("evidence_uri"),
        "evidence_range": edge.get("evidence_range_json"),
        "confidence": edge["confidence"],
    }


def build_symbol_context(conn: sqlite3.Connection, node_id: str) -> SymbolContext | None:
    """Build context for a symbol by its ID.
    
    Assembles the focus symbol, structural and lexical relationships,
    edges, file siblings, and metadata summaries.
    
    Args:
        conn: SQLite connection.
        node_id: ID of the symbol to build context for.
        
    Returns:
        SymbolContext if symbol exists, None otherwise.
    """
    # Step 1: Fetch focus symbol
    focus_node = get_symbol(conn, node_id)
    if focus_node is None:
        return None
    
    focus_symbol = adapt_node_to_symbol(focus_node)
    
    # Step 2: Fetch structural parent
    structural_parent_node = get_parent_symbol(conn, focus_node)
    structural_parent = adapt_node_to_symbol(structural_parent_node) if structural_parent_node else None
    
    # Step 3: Fetch structural children
    structural_children_nodes = get_child_symbols(conn, node_id)
    structural_children = [adapt_node_to_symbol(n) for n in structural_children_nodes]
    
    # Step 4: Fetch lexical parent
    lexical_parent_node = get_lexical_parent_symbol(conn, focus_node)
    lexical_parent = adapt_node_to_symbol(lexical_parent_node) if lexical_parent_node else None
    
    # Step 5: Fetch lexical children
    lexical_children_nodes = get_lexical_child_symbols(conn, node_id)
    lexical_children = [adapt_node_to_symbol(n) for n in lexical_children_nodes]
    
    # Step 6: Fetch outgoing edges
    outgoing_edges_raw = get_outgoing_edges(conn, node_id)
    outgoing_edges = [adapt_edge_to_context_edge(e) for e in outgoing_edges_raw]
    
    # Step 7: Fetch incoming edges
    incoming_edges_raw = get_incoming_edges(conn, node_id)
    incoming_edges = [adapt_edge_to_context_edge(e) for e in incoming_edges_raw]
    
    # Step 8: Fetch file siblings
    file_id = focus_node["file_id"]
    all_file_symbols = get_symbols_for_file(conn, file_id)
    file_siblings = [
        adapt_node_to_symbol(n) for n in all_file_symbols
        if n["id"] != node_id
    ]
    
    # Create context object
    context = SymbolContext(
        focus_symbol=focus_symbol,
        structural_parent=structural_parent,
        structural_children=structural_children,
        lexical_parent=lexical_parent,
        lexical_children=lexical_children,
        incoming_edges=incoming_edges,
        outgoing_edges=outgoing_edges,
        file_siblings=file_siblings,
    )

    # Step 9: Build structural summary
    context.structural_summary = build_structural_summary(context)

    # Step 10: Build freshness
    context.freshness = build_freshness(context, focus_node)

    # Step 11: Build confidence
    context.confidence = build_confidence(context)

    # Step 12: Build reference summary
    context.reference_summary = build_reference_stats(conn, node_id)

    return context
