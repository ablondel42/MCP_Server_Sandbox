"""Graph-level transactional helpers."""

import sqlite3

from repo_context.storage.nodes import upsert_nodes, delete_nodes_for_file
from repo_context.storage.edges import upsert_edges, delete_edges_for_file


def replace_file_graph(
    conn: sqlite3.Connection,
    file_id: str,
    nodes: list[dict],
    edges: list[dict],
) -> None:
    """Replace the entire graph state for one file.

    This function performs a complete replacement of all nodes and edges
    owned by a file. It uses a transaction to ensure atomicity.

    Transaction order:
    1. BEGIN transaction
    2. DELETE edges for file_id (must be before node deletion)
    3. DELETE nodes for file_id
    4. INSERT fresh nodes
    5. INSERT fresh edges
    6. COMMIT on success / ROLLBACK on failure

    Args:
        conn: SQLite connection.
        file_id: File ID to replace graph for.
        nodes: List of node dictionaries to insert.
        edges: List of edge dictionaries to insert.

    Raises:
        Exception: Re-raises the original exception after rollback.
    """
    # Note: We don't explicitly BEGIN since the caller may already be in a transaction
    # SQLite will implicitly create a transaction on the first write operation
    
    try:
        # Delete edges first (before nodes)
        delete_edges_for_file(conn, file_id)

        # Delete nodes
        delete_nodes_for_file(conn, file_id)

        # Insert fresh nodes
        upsert_nodes(conn, nodes)  # type: ignore

        # Insert fresh edges
        upsert_edges(conn, edges)  # type: ignore

        conn.commit()
    except Exception:
        conn.rollback()
        raise
