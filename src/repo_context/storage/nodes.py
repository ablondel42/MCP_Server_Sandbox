"""Node persistence helpers."""

import sqlite3


def upsert_node(conn: sqlite3.Connection, node: dict) -> None:
    """Insert or update a single node.
    
    Args:
        conn: SQLite connection.
        node: Node dictionary with all required fields.
    """
    conn.execute(
        """
        INSERT INTO nodes (
            id, repo_id, file_id, language, kind, name, qualified_name, uri,
            range_json, selection_range_json, parent_id, visibility_hint,
            doc_summary, content_hash, semantic_hash, source, confidence,
            payload_json, last_indexed_at
        ) VALUES (
            :id, :repo_id, :file_id, :language, :kind, :name, :qualified_name, :uri,
            :range_json, :selection_range_json, :parent_id, :visibility_hint,
            :doc_summary, :content_hash, :semantic_hash, :source, :confidence,
            :payload_json, :last_indexed_at
        )
        ON CONFLICT(id) DO UPDATE SET
            repo_id = excluded.repo_id,
            file_id = excluded.file_id,
            language = excluded.language,
            kind = excluded.kind,
            name = excluded.name,
            qualified_name = excluded.qualified_name,
            uri = excluded.uri,
            range_json = excluded.range_json,
            selection_range_json = excluded.selection_range_json,
            parent_id = excluded.parent_id,
            visibility_hint = excluded.visibility_hint,
            doc_summary = excluded.doc_summary,
            content_hash = excluded.content_hash,
            semantic_hash = excluded.semantic_hash,
            source = excluded.source,
            confidence = excluded.confidence,
            payload_json = excluded.payload_json,
            last_indexed_at = excluded.last_indexed_at
        """,
        node,
    )


def upsert_nodes(conn: sqlite3.Connection, nodes: list[dict]) -> None:
    """Insert or update multiple nodes.
    
    Args:
        conn: SQLite connection.
        nodes: List of node dictionaries.
    """
    for node in nodes:
        upsert_node(conn, node)


def list_nodes_for_file(conn: sqlite3.Connection, file_id: str) -> list[dict]:
    """List all nodes for a specific file.
    
    Args:
        conn: SQLite connection.
        file_id: File ID to filter by.
        
    Returns:
        List of node dictionaries.
    """
    cursor = conn.execute(
        """
        SELECT id, repo_id, file_id, language, kind, name, qualified_name, uri,
               range_json, selection_range_json, parent_id, visibility_hint,
               doc_summary, content_hash, semantic_hash, source, confidence,
               payload_json, last_indexed_at
        FROM nodes
        WHERE file_id = ?
        ORDER BY kind, qualified_name
        """,
        (file_id,),
    )
    
    return [dict(row) for row in cursor.fetchall()]


def delete_nodes_for_file(conn: sqlite3.Connection, file_id: str) -> None:
    """Delete all nodes for a specific file.
    
    Args:
        conn: SQLite connection.
        file_id: File ID to delete nodes for.
    """
    conn.execute("DELETE FROM nodes WHERE file_id = ?", (file_id,))
