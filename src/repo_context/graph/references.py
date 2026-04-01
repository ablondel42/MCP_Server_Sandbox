"""Graph queries for reference edges."""


def list_reference_edges_for_target(conn, target_id: str):
    """List all reference edges pointing to a target symbol.

    Args:
        conn: SQLite connection.
        target_id: Target symbol ID.

    Returns:
        List of reference edge dicts ordered by evidence URI, line, character.
    """
    cursor = conn.execute(
        """
        SELECT id, repo_id, kind, from_id, to_id, source, confidence,
               evidence_file_id, evidence_uri, evidence_range_json,
               payload_json, last_indexed_at
        FROM edges
        WHERE kind = 'references' AND to_id = ?
        ORDER BY evidence_uri,
                 json_extract(evidence_range_json, '$.start.line'),
                 json_extract(evidence_range_json, '$.start.character'),
                 id
        """,
        (target_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def list_referenced_by(conn, target_id: str):
    """List symbols that reference this target (reverse lookup).

    Args:
        conn: SQLite connection.
        target_id: Target symbol ID.

    Returns:
        List of source symbol dicts that reference this target.
    """
    cursor = conn.execute(
        """
        SELECT DISTINCT n.id, n.repo_id, n.file_id, n.language, n.kind, n.name,
               n.qualified_name, n.uri, n.scope, n.lexical_parent_id
        FROM edges e
        JOIN nodes n ON e.from_id = n.id
        WHERE e.kind = 'references' AND e.to_id = ?
        ORDER BY n.kind, n.qualified_name, n.id
        """,
        (target_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def list_references_from_symbol(conn, source_id: str):
    """List all references FROM a source symbol.

    Args:
        conn: SQLite connection.
        source_id: Source symbol ID.

    Returns:
        List of reference edge dicts ordered by to_id.
    """
    cursor = conn.execute(
        """
        SELECT id, repo_id, kind, from_id, to_id, source, confidence,
               evidence_file_id, evidence_uri, evidence_range_json,
               payload_json, last_indexed_at
        FROM edges
        WHERE kind = 'references' AND from_id = ?
        ORDER BY to_id, evidence_uri, id
        """,
        (source_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def build_reference_stats(conn, target_id: str) -> dict:
    """Build reference statistics for a target symbol.

    Args:
        conn: SQLite connection.
        target_id: Target symbol ID.

    Returns:
        Stats dict with counts and availability info.
    """
    # Get reference count
    cursor = conn.execute(
        "SELECT COUNT(*) FROM edges WHERE kind = 'references' AND to_id = ?",
        (target_id,),
    )
    reference_count = cursor.fetchone()[0]

    # Get referencing file count
    cursor = conn.execute(
        "SELECT COUNT(DISTINCT evidence_file_id) FROM edges WHERE kind = 'references' AND to_id = ?",
        (target_id,),
    )
    referencing_file_count = cursor.fetchone()[0]

    # Get referencing module count
    cursor = conn.execute(
        """
        SELECT COUNT(DISTINCT n.file_id)
        FROM edges e
        JOIN nodes n ON e.from_id = n.id
        WHERE e.kind = 'references' AND e.to_id = ?
        """,
        (target_id,),
    )
    referencing_module_count = cursor.fetchone()[0]

    # Get refresh state
    refresh_state = get_reference_refresh_state(conn, target_id)

    return {
        "reference_count": reference_count,
        "referencing_file_count": referencing_file_count,
        "referencing_module_count": referencing_module_count,
        "available": refresh_state["available"],
        "last_refreshed_at": refresh_state["last_refreshed_at"],
    }


def get_reference_refresh_state(conn, target_id: str) -> dict:
    """Get reference refresh state for a target symbol.

    Args:
        conn: SQLite connection.
        target_id: Target symbol ID.

    Returns:
        Refresh state dict. Never refreshed returns available=False.
    """
    row = conn.execute(
        """
        SELECT target_symbol_id, available, last_refreshed_at, refresh_status, error_code
        FROM reference_refresh
        WHERE target_symbol_id = ?
        """,
        (target_id,),
    ).fetchone()

    if not row:
        return {
            "target_symbol_id": target_id,
            "available": False,
            "last_refreshed_at": None,
            "refresh_status": None,
            "error_code": None,
        }
    return {
        "target_symbol_id": row["target_symbol_id"],
        "available": bool(row["available"]),
        "last_refreshed_at": row["last_refreshed_at"],
        "refresh_status": row["refresh_status"],
        "error_code": row["error_code"],
    }
