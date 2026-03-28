"""Edge persistence helpers."""

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


def edge_to_row(edge: dict) -> dict:
    """Convert edge dictionary to database row values.
    
    Serializes JSON fields and prepares all values for storage.
    
    Args:
        edge: Edge dictionary with all fields.
        
    Returns:
        Dictionary suitable for database insertion.
    """
    return {
        "id": edge["id"],
        "repo_id": edge["repo_id"],
        "kind": edge["kind"],
        "from_id": edge["from_id"],
        "to_id": edge["to_id"],
        "source": edge["source"],
        "confidence": edge["confidence"],
        "evidence_file_id": edge.get("evidence_file_id"),
        "evidence_uri": edge.get("evidence_uri"),
        "evidence_range_json": _serialize_json(edge.get("evidence_range_json")),
        "payload_json": _serialize_json(edge.get("payload_json", {})),
        "last_indexed_at": edge.get("last_indexed_at"),
    }


def row_to_edge(row: sqlite3.Row) -> dict:
    """Convert database row to edge dictionary.
    
    Deserializes JSON fields and reconstructs edge structure.
    
    Args:
        row: SQLite row from database query.
        
    Returns:
        Edge dictionary with deserialized fields.
    """
    return {
        "id": row["id"],
        "repo_id": row["repo_id"],
        "kind": row["kind"],
        "from_id": row["from_id"],
        "to_id": row["to_id"],
        "source": row["source"],
        "confidence": row["confidence"],
        "evidence_file_id": row["evidence_file_id"],
        "evidence_uri": row["evidence_uri"],
        "evidence_range_json": _deserialize_json(row["evidence_range_json"]),
        "payload_json": _deserialize_json(row["payload_json"]),
        "last_indexed_at": row["last_indexed_at"],
    }


def upsert_edge(conn: sqlite3.Connection, edge: dict) -> None:
    """Insert or update a single edge.

    Args:
        conn: SQLite connection.
        edge: Edge dictionary with all required fields.
    """
    row = edge_to_row(edge)
    conn.execute(
        """
        INSERT INTO edges (
            id, repo_id, kind, from_id, to_id, source, confidence,
            evidence_file_id, evidence_uri, evidence_range_json,
            payload_json, last_indexed_at
        ) VALUES (
            :id, :repo_id, :kind, :from_id, :to_id, :source, :confidence,
            :evidence_file_id, :evidence_uri, :evidence_range_json,
            :payload_json, :last_indexed_at
        )
        ON CONFLICT(id) DO UPDATE SET
            repo_id = excluded.repo_id,
            kind = excluded.kind,
            from_id = excluded.from_id,
            to_id = excluded.to_id,
            source = excluded.source,
            confidence = excluded.confidence,
            evidence_file_id = excluded.evidence_file_id,
            evidence_uri = excluded.evidence_uri,
            evidence_range_json = excluded.evidence_range_json,
            payload_json = excluded.payload_json,
            last_indexed_at = excluded.last_indexed_at
        """,
        row,
    )


def upsert_edges(conn: sqlite3.Connection, edges: list[dict]) -> None:
    """Insert or update multiple edges.

    Args:
        conn: SQLite connection.
        edges: List of edge dictionaries.
    """
    for edge in edges:
        upsert_edge(conn, edge)


def get_edge_by_id(conn: sqlite3.Connection, edge_id: str) -> dict | None:
    """Get an edge by its ID.
    
    Args:
        conn: SQLite connection.
        edge_id: Edge ID to fetch.
        
    Returns:
        Edge dictionary or None if not found.
    """
    cursor = conn.execute(
        """
        SELECT id, repo_id, kind, from_id, to_id, source, confidence,
               evidence_file_id, evidence_uri, evidence_range_json,
               payload_json, last_indexed_at
        FROM edges
        WHERE id = ?
        """,
        (edge_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return row_to_edge(row)


def list_edges_for_repo(conn: sqlite3.Connection, repo_id: str) -> list[dict]:
    """List all edges for a specific repository.

    Args:
        conn: SQLite connection.
        repo_id: Repository ID to filter by.

    Returns:
        List of edge dictionaries ordered by kind, from_id, to_id, id.
    """
    cursor = conn.execute(
        """
        SELECT id, repo_id, kind, from_id, to_id, source, confidence,
               evidence_file_id, evidence_uri, evidence_range_json,
               payload_json, last_indexed_at
        FROM edges
        WHERE repo_id = ?
        ORDER BY kind, from_id, to_id, id
        """,
        (repo_id,),
    )
    return [row_to_edge(row) for row in cursor.fetchall()]


def list_outgoing_edges(
    conn: sqlite3.Connection,
    from_id: str,
    kind: str | None = None,
) -> list[dict]:
    """List outgoing edges from a node.
    
    Args:
        conn: SQLite connection.
        from_id: Source node ID to filter by.
        kind: Optional edge kind filter.
        
    Returns:
        List of edge dictionaries ordered by kind, to_id, id.
    """
    if kind is not None:
        cursor = conn.execute(
            """
            SELECT id, repo_id, kind, from_id, to_id, source, confidence,
                   evidence_file_id, evidence_uri, evidence_range_json,
                   payload_json, last_indexed_at
            FROM edges
            WHERE from_id = ? AND kind = ?
            ORDER BY kind, to_id, id
            """,
            (from_id, kind),
        )
    else:
        cursor = conn.execute(
            """
            SELECT id, repo_id, kind, from_id, to_id, source, confidence,
                   evidence_file_id, evidence_uri, evidence_range_json,
                   payload_json, last_indexed_at
            FROM edges
            WHERE from_id = ?
            ORDER BY kind, to_id, id
            """,
            (from_id,),
        )
    return [row_to_edge(row) for row in cursor.fetchall()]


def list_incoming_edges(
    conn: sqlite3.Connection,
    to_id: str,
    kind: str | None = None,
) -> list[dict]:
    """List incoming edges to a node.
    
    Args:
        conn: SQLite connection.
        to_id: Target node ID to filter by.
        kind: Optional edge kind filter.
        
    Returns:
        List of edge dictionaries ordered by kind, from_id, id.
    """
    if kind is not None:
        cursor = conn.execute(
            """
            SELECT id, repo_id, kind, from_id, to_id, source, confidence,
                   evidence_file_id, evidence_uri, evidence_range_json,
                   payload_json, last_indexed_at
            FROM edges
            WHERE to_id = ? AND kind = ?
            ORDER BY kind, from_id, id
            """,
            (to_id, kind),
        )
    else:
        cursor = conn.execute(
            """
            SELECT id, repo_id, kind, from_id, to_id, source, confidence,
                   evidence_file_id, evidence_uri, evidence_range_json,
                   payload_json, last_indexed_at
            FROM edges
            WHERE to_id = ?
            ORDER BY kind, from_id, id
            """,
            (to_id,),
        )
    return [row_to_edge(row) for row in cursor.fetchall()]


def list_edges_for_file(conn: sqlite3.Connection, file_id: str) -> list[dict]:
    """List all edges with evidence in a specific file.
    
    Args:
        conn: SQLite connection.
        file_id: File ID to filter by.
        
    Returns:
        List of edge dictionaries ordered by kind, from_id, to_id, id.
    """
    cursor = conn.execute(
        """
        SELECT id, repo_id, kind, from_id, to_id, source, confidence,
               evidence_file_id, evidence_uri, evidence_range_json,
               payload_json, last_indexed_at
        FROM edges
        WHERE evidence_file_id = ?
        ORDER BY kind, from_id, to_id, id
        """,
        (file_id,),
    )
    return [row_to_edge(row) for row in cursor.fetchall()]


def delete_edges_for_file(conn: sqlite3.Connection, file_id: str) -> None:
    """Delete all edges associated with a specific file.

    Args:
        conn: SQLite connection.
        file_id: File ID to delete edges for.
    """
    conn.execute("DELETE FROM edges WHERE evidence_file_id = ?", (file_id,))
