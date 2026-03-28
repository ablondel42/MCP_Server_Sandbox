"""Graph query layer for symbol and edge retrieval."""

import sqlite3

from repo_context.storage.nodes import (
    get_node_by_id,
    get_node_by_qualified_name,
    list_nodes_for_file,
    list_nodes_for_repo,
    list_child_nodes,
    list_lexical_children,
)
from repo_context.storage.edges import (
    get_edge_by_id,
    list_edges_for_repo,
    list_outgoing_edges,
    list_incoming_edges,
    list_edges_for_file,
)


CALLABLE_KINDS = {
    "function",
    "async_function",
    "method",
    "async_method",
    "local_function",
    "local_async_function",
}

LOCAL_CALLABLE_KINDS = {"local_function", "local_async_function"}


def get_symbol(conn: sqlite3.Connection, node_id: str) -> dict | None:
    """Get a symbol by its ID.
    
    Args:
        conn: SQLite connection.
        node_id: Symbol/node ID.
        
    Returns:
        Symbol dictionary or None if not found.
    """
    return get_node_by_id(conn, node_id)


def get_symbol_by_qualified_name(
    conn: sqlite3.Connection,
    repo_id: str,
    qualified_name: str,
    kind: str | None = None,
) -> dict | None:
    """Get a symbol by qualified name.
    
    Args:
        conn: SQLite connection.
        repo_id: Repository ID.
        qualified_name: Symbol qualified name.
        kind: Optional kind filter for disambiguation.
        
    Returns:
        Symbol dictionary or None if not found or ambiguous.
    """
    return get_node_by_qualified_name(conn, repo_id, qualified_name, kind)


def get_parent_symbol(conn: sqlite3.Connection, node: dict) -> dict | None:
    """Get the structural parent symbol of a node.
    
    Args:
        conn: SQLite connection.
        node: Node dictionary with parent_id field.
        
    Returns:
        Parent symbol dictionary or None if no parent.
    """
    parent_id = node.get("parent_id")
    if parent_id is None:
        return None
    return get_node_by_id(conn, parent_id)


def get_child_symbols(conn: sqlite3.Connection, node_id: str) -> list[dict]:
    """Get structural child symbols of a node.
    
    Args:
        conn: SQLite connection.
        node_id: Node ID to get children for.
        
    Returns:
        List of child symbol dictionaries.
    """
    return list_child_nodes(conn, node_id)


def get_lexical_parent_symbol(conn: sqlite3.Connection, node: dict) -> dict | None:
    """Get the lexical parent symbol of a node.
    
    Args:
        conn: SQLite connection.
        node: Node dictionary with lexical_parent_id field.
        
    Returns:
        Lexical parent symbol dictionary or None if no parent.
    """
    lexical_parent_id = node.get("lexical_parent_id")
    if lexical_parent_id is None:
        return None
    return get_node_by_id(conn, lexical_parent_id)


def get_lexical_child_symbols(conn: sqlite3.Connection, node_id: str) -> list[dict]:
    """Get lexical child symbols of a node.
    
    Args:
        conn: SQLite connection.
        node_id: Node ID to get lexical children for.
        
    Returns:
        List of lexical child symbol dictionaries.
    """
    return list_lexical_children(conn, node_id)


def get_outgoing_edges(
    conn: sqlite3.Connection,
    node_id: str,
    kind: str | None = None,
) -> list[dict]:
    """Get outgoing edges from a node.
    
    Args:
        conn: SQLite connection.
        node_id: Source node ID.
        kind: Optional edge kind filter.
        
    Returns:
        List of edge dictionaries.
    """
    return list_outgoing_edges(conn, node_id, kind)


def get_incoming_edges(
    conn: sqlite3.Connection,
    node_id: str,
    kind: str | None = None,
) -> list[dict]:
    """Get incoming edges to a node.
    
    Args:
        conn: SQLite connection.
        node_id: Target node ID.
        kind: Optional edge kind filter.
        
    Returns:
        List of edge dictionaries.
    """
    return list_incoming_edges(conn, node_id, kind)


def get_symbols_for_file(conn: sqlite3.Connection, file_id: str) -> list[dict]:
    """Get all symbols for a specific file.
    
    Args:
        conn: SQLite connection.
        file_id: File ID.
        
    Returns:
        List of symbol dictionaries.
    """
    return list_nodes_for_file(conn, file_id)


def get_repo_graph_stats(conn: sqlite3.Connection, repo_id: str) -> dict:
    """Get graph statistics for a repository.
    
    Args:
        conn: SQLite connection.
        repo_id: Repository ID.
        
    Returns:
        Dictionary with counts:
        - repo_id
        - node_count
        - edge_count
        - module_count
        - class_count
        - callable_count (includes local functions)
        - local_callable_count
    """
    # Get node counts by kind
    cursor = conn.execute(
        """
        SELECT kind, COUNT(*) as count
        FROM nodes
        WHERE repo_id = ?
        GROUP BY kind
        """,
        (repo_id,),
    )
    kind_counts = {row["kind"]: row["count"] for row in cursor.fetchall()}
    
    # Get total node count
    cursor = conn.execute(
        "SELECT COUNT(*) as count FROM nodes WHERE repo_id = ?",
        (repo_id,),
    )
    node_count = cursor.fetchone()["count"]
    
    # Get total edge count
    cursor = conn.execute(
        "SELECT COUNT(*) as count FROM edges WHERE repo_id = ?",
        (repo_id,),
    )
    edge_count = cursor.fetchone()["count"]
    
    # Calculate callable count (all callable kinds including local)
    callable_count = sum(
        kind_counts.get(k, 0) for k in CALLABLE_KINDS
    )
    
    # Calculate local callable count
    local_callable_count = sum(
        kind_counts.get(k, 0) for k in LOCAL_CALLABLE_KINDS
    )
    
    return {
        "repo_id": repo_id,
        "node_count": node_count,
        "edge_count": edge_count,
        "module_count": kind_counts.get("module", 0),
        "class_count": kind_counts.get("class", 0),
        "callable_count": callable_count,
        "local_callable_count": local_callable_count,
    }
