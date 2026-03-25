"""Edge persistence helpers."""

import sqlite3


def upsert_edge(conn: sqlite3.Connection, edge: dict) -> None:
    """Insert or update a single edge.
    
    Args:
        conn: SQLite connection.
        edge: Edge dictionary with all required fields.
    """
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
        edge,
    )


def upsert_edges(conn: sqlite3.Connection, edges: list[dict]) -> None:
    """Insert or update multiple edges.
    
    Args:
        conn: SQLite connection.
        edges: List of edge dictionaries.
    """
    for edge in edges:
        upsert_edge(conn, edge)


def list_edges_for_repo(conn: sqlite3.Connection, repo_id: str) -> list[dict]:
    """List all edges for a specific repository.
    
    Args:
        conn: SQLite connection.
        repo_id: Repository ID to filter by.
        
    Returns:
        List of edge dictionaries.
    """
    cursor = conn.execute(
        """
        SELECT id, repo_id, kind, from_id, to_id, source, confidence,
               evidence_file_id, evidence_uri, evidence_range_json,
               payload_json, last_indexed_at
        FROM edges
        WHERE repo_id = ?
        ORDER BY kind, from_id, to_id
        """,
        (repo_id,),
    )
    
    return [dict(row) for row in cursor.fetchall()]


def delete_edges_for_file(conn: sqlite3.Connection, file_id: str) -> None:
    """Delete all edges associated with a specific file.
    
    Args:
        conn: SQLite connection.
        file_id: File ID to delete edges for.
    """
    conn.execute("DELETE FROM edges WHERE evidence_file_id = ?", (file_id,))
