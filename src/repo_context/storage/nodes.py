"""Node persistence helpers with nested scope support."""

import json
import sqlite3
from typing import Any


def _serialize_json(value: Any) -> str | None:
    """Serialize a value to JSON string.
    
    Args:
        value: Value to serialize.
        
    Returns:
        JSON string or None if value is None.
    """
    if value is None:
        return None
    return json.dumps(value, sort_keys=True)


def _deserialize_json(value: str | None) -> Any:
    """Deserialize a JSON string to Python object.
    
    Args:
        value: JSON string or None.
        
    Returns:
        Python object or None if value is None.
    """
    if value is None:
        return None
    return json.loads(value)


def node_to_row(node: dict) -> dict:
    """Convert node dictionary to database row values.
    
    Serializes JSON fields and prepares all values for storage.
    
    Args:
        node: Node dictionary with all fields.
        
    Returns:
        Dictionary suitable for database insertion.
    """
    return {
        "id": node["id"],
        "repo_id": node["repo_id"],
        "file_id": node["file_id"],
        "language": node["language"],
        "kind": node["kind"],
        "name": node["name"],
        "qualified_name": node["qualified_name"],
        "uri": node["uri"],
        "range_json": _serialize_json(node.get("range_json")),
        "selection_range_json": _serialize_json(node.get("selection_range_json")),
        "parent_id": node.get("parent_id"),
        "visibility_hint": node.get("visibility_hint"),
        "doc_summary": node.get("doc_summary"),
        "content_hash": node["content_hash"],
        "semantic_hash": node["semantic_hash"],
        "source": node["source"],
        "confidence": node["confidence"],
        "payload_json": _serialize_json(node.get("payload_json", {})),
        "scope": node.get("scope"),
        "lexical_parent_id": node.get("lexical_parent_id"),
        "last_indexed_at": node.get("last_indexed_at"),
    }


def row_to_node(row: sqlite3.Row) -> dict:
    """Convert database row to node dictionary.
    
    Deserializes JSON fields and reconstructs node structure.
    
    Args:
        row: SQLite row from database query.
        
    Returns:
        Node dictionary with deserialized fields.
    """
    return {
        "id": row["id"],
        "repo_id": row["repo_id"],
        "file_id": row["file_id"],
        "language": row["language"],
        "kind": row["kind"],
        "name": row["name"],
        "qualified_name": row["qualified_name"],
        "uri": row["uri"],
        "range_json": _deserialize_json(row["range_json"]),
        "selection_range_json": _deserialize_json(row["selection_range_json"]),
        "parent_id": row["parent_id"],
        "visibility_hint": row["visibility_hint"],
        "doc_summary": row["doc_summary"],
        "content_hash": row["content_hash"],
        "semantic_hash": row["semantic_hash"],
        "source": row["source"],
        "confidence": row["confidence"],
        "payload_json": _deserialize_json(row["payload_json"]),
        "scope": row["scope"],
        "lexical_parent_id": row["lexical_parent_id"],
        "last_indexed_at": row["last_indexed_at"],
    }


def upsert_node(conn: sqlite3.Connection, node: dict) -> None:
    """Insert or update a single node.

    Args:
        conn: SQLite connection.
        node: Node dictionary with all required fields.
    """
    row = node_to_row(node)
    conn.execute(
        """
        INSERT INTO nodes (
            id, repo_id, file_id, language, kind, name, qualified_name, uri,
            range_json, selection_range_json, parent_id, visibility_hint,
            doc_summary, content_hash, semantic_hash, source, confidence,
            payload_json, scope, lexical_parent_id, last_indexed_at
        ) VALUES (
            :id, :repo_id, :file_id, :language, :kind, :name, :qualified_name, :uri,
            :range_json, :selection_range_json, :parent_id, :visibility_hint,
            :doc_summary, :content_hash, :semantic_hash, :source, :confidence,
            :payload_json, :scope, :lexical_parent_id, :last_indexed_at
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
            scope = excluded.scope,
            lexical_parent_id = excluded.lexical_parent_id,
            last_indexed_at = excluded.last_indexed_at
        """,
        row,
    )


def upsert_nodes(conn: sqlite3.Connection, nodes: list[dict]) -> None:
    """Insert or update multiple nodes.

    Args:
        conn: SQLite connection.
        nodes: List of node dictionaries.
    """
    for node in nodes:
        upsert_node(conn, node)


def get_node_by_id(conn: sqlite3.Connection, node_id: str) -> dict | None:
    """Get a node by its ID.
    
    Args:
        conn: SQLite connection.
        node_id: Node ID to fetch.
        
    Returns:
        Node dictionary or None if not found.
    """
    cursor = conn.execute(
        """
        SELECT id, repo_id, file_id, language, kind, name, qualified_name, uri,
               range_json, selection_range_json, parent_id, visibility_hint,
               doc_summary, content_hash, semantic_hash, source, confidence,
               payload_json, scope, lexical_parent_id, last_indexed_at
        FROM nodes
        WHERE id = ?
        """,
        (node_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return row_to_node(row)


def get_node_by_qualified_name(
    conn: sqlite3.Connection,
    repo_id: str,
    qualified_name: str,
    kind: str | None = None,
) -> dict | None:
    """Get a node by qualified name.
    
    Args:
        conn: SQLite connection.
        repo_id: Repository ID to filter by.
        qualified_name: Qualified name to search for.
        kind: Optional kind filter for disambiguation.
        
    Returns:
        Node dictionary or None if not found or ambiguous.
    """
    if kind is not None:
        cursor = conn.execute(
            """
            SELECT id, repo_id, file_id, language, kind, name, qualified_name, uri,
                   range_json, selection_range_json, parent_id, visibility_hint,
                   doc_summary, content_hash, semantic_hash, source, confidence,
                   payload_json, scope, lexical_parent_id, last_indexed_at
            FROM nodes
            WHERE repo_id = ? AND qualified_name = ? AND kind = ?
            """,
            (repo_id, qualified_name, kind),
        )
    else:
        cursor = conn.execute(
            """
            SELECT id, repo_id, file_id, language, kind, name, qualified_name, uri,
                   range_json, selection_range_json, parent_id, visibility_hint,
                   doc_summary, content_hash, semantic_hash, source, confidence,
                   payload_json, scope, lexical_parent_id, last_indexed_at
            FROM nodes
            WHERE repo_id = ? AND qualified_name = ?
            """,
            (repo_id, qualified_name),
        )
    
    rows = cursor.fetchall()
    if len(rows) == 0:
        return None
    if len(rows) > 1:
        # Ambiguous - multiple nodes with same qualified_name
        return None
    return row_to_node(rows[0])


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
               payload_json, scope, lexical_parent_id, last_indexed_at
        FROM nodes
        WHERE file_id = ?
        ORDER BY kind, qualified_name, id
        """,
        (file_id,),
    )
    return [row_to_node(row) for row in cursor.fetchall()]


def list_nodes_for_repo(conn: sqlite3.Connection, repo_id: str) -> list[dict]:
    """List all nodes for a specific repository.

    Args:
        conn: SQLite connection.
        repo_id: Repository ID to filter by.

    Returns:
        List of node dictionaries ordered by kind, qualified_name, id.
    """
    cursor = conn.execute(
        """
        SELECT id, repo_id, file_id, language, kind, name, qualified_name, uri,
               range_json, selection_range_json, parent_id, visibility_hint,
               doc_summary, content_hash, semantic_hash, source, confidence,
               payload_json, scope, lexical_parent_id, last_indexed_at
        FROM nodes
        WHERE repo_id = ?
        ORDER BY kind, qualified_name, id
        """,
        (repo_id,),
    )
    return [row_to_node(row) for row in cursor.fetchall()]


def find_nodes_by_name(
    conn: sqlite3.Connection,
    repo_id: str,
    name_pattern: str,
    kind: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Find nodes by name or qualified name pattern.

    Args:
        conn: SQLite connection.
        repo_id: Repository ID to filter by.
        name_pattern: Name or qualified name pattern (supports % wildcard).
        kind: Optional symbol kind filter.
        limit: Maximum number of results to return.

    Returns:
        List of matching node dictionaries ordered by kind, qualified_name, id.
    """
    if kind is not None:
        cursor = conn.execute(
            """
            SELECT id, repo_id, file_id, language, kind, name, qualified_name, uri,
                   range_json, selection_range_json, parent_id, visibility_hint,
                   doc_summary, content_hash, semantic_hash, source, confidence,
                   payload_json, scope, lexical_parent_id, last_indexed_at
            FROM nodes
            WHERE repo_id = ? AND (name LIKE ? OR qualified_name LIKE ?) AND kind = ?
            ORDER BY kind, qualified_name, id
            LIMIT ?
            """,
            (repo_id, name_pattern, name_pattern, kind, limit),
        )
    else:
        cursor = conn.execute(
            """
            SELECT id, repo_id, file_id, language, kind, name, qualified_name, uri,
                   range_json, selection_range_json, parent_id, visibility_hint,
                   doc_summary, content_hash, semantic_hash, source, confidence,
                   payload_json, scope, lexical_parent_id, last_indexed_at
            FROM nodes
            WHERE repo_id = ? AND (name LIKE ? OR qualified_name LIKE ?)
            ORDER BY kind, qualified_name, id
            LIMIT ?
            """,
            (repo_id, name_pattern, name_pattern, limit),
        )
    return [row_to_node(row) for row in cursor.fetchall()]


def list_child_nodes(conn: sqlite3.Connection, parent_id: str) -> list[dict]:
    """List structural child nodes by parent_id.
    
    Args:
        conn: SQLite connection.
        parent_id: Structural parent ID to filter by.
        
    Returns:
        List of child node dictionaries ordered by kind, name, id.
    """
    cursor = conn.execute(
        """
        SELECT id, repo_id, file_id, language, kind, name, qualified_name, uri,
               range_json, selection_range_json, parent_id, visibility_hint,
               doc_summary, content_hash, semantic_hash, source, confidence,
               payload_json, scope, lexical_parent_id, last_indexed_at
        FROM nodes
        WHERE parent_id = ?
        ORDER BY kind, name, id
        """,
        (parent_id,),
    )
    return [row_to_node(row) for row in cursor.fetchall()]


def list_lexical_children(conn: sqlite3.Connection, lexical_parent_id: str) -> list[dict]:
    """List lexical child nodes by lexical_parent_id.
    
    Args:
        conn: SQLite connection.
        lexical_parent_id: Lexical parent ID to filter by.
        
    Returns:
        List of lexical child node dictionaries ordered by kind, name, id.
    """
    cursor = conn.execute(
        """
        SELECT id, repo_id, file_id, language, kind, name, qualified_name, uri,
               range_json, selection_range_json, parent_id, visibility_hint,
               doc_summary, content_hash, semantic_hash, source, confidence,
               payload_json, scope, lexical_parent_id, last_indexed_at
        FROM nodes
        WHERE lexical_parent_id = ?
        ORDER BY kind, name, id
        """,
        (lexical_parent_id,),
    )
    return [row_to_node(row) for row in cursor.fetchall()]


def delete_nodes_for_file(conn: sqlite3.Connection, file_id: str) -> None:
    """Delete all nodes for a specific file.

    Args:
        conn: SQLite connection.
        file_id: File ID to delete nodes for.
    """
    conn.execute("DELETE FROM nodes WHERE file_id = ?", (file_id,))
