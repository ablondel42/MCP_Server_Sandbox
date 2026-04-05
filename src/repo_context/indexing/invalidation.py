"""Reference invalidation helpers.

When a file changes, references whose evidence comes from that file
become stale and must be invalidated.
"""

import sqlite3


def mark_symbols_in_file_stale(conn: sqlite3.Connection, file_id: str) -> list[str]:
    """Mark reference state for symbols declared in a file as stale.

    Updates the reference_refresh table to mark symbols as unavailable
    after their declaring file has changed.

    Args:
        conn: SQLite connection.
        file_id: ID of the changed file.

    Returns:
        List of symbol IDs that were marked stale.
    """
    # Get all symbol IDs declared in this file
    cursor = conn.execute(
        "SELECT id FROM nodes WHERE file_id = ?",
        (file_id,),
    )
    symbol_ids = [row["id"] for row in cursor.fetchall()]

    if not symbol_ids:
        return []

    # Update reference_refresh to mark as unavailable
    placeholders = ",".join("?" * len(symbol_ids))
    conn.execute(
        f"""
        INSERT OR REPLACE INTO reference_refresh (target_symbol_id, available, last_refreshed_at)
        SELECT id, 0, NULL
        FROM nodes
        WHERE id IN ({placeholders})
        AND id NOT IN (
            SELECT target_symbol_id FROM reference_refresh
            WHERE target_symbol_id IN ({placeholders})
        )
        """,
        symbol_ids + symbol_ids,
    )

    # Also update existing records
    conn.execute(
        f"""
        UPDATE reference_refresh
        SET available = 0, last_refreshed_at = NULL
        WHERE target_symbol_id IN ({placeholders})
        """,
        symbol_ids,
    )

    return symbol_ids


def invalidate_reference_summaries_for_file(conn: sqlite3.Connection, file_id: str) -> int:
    """Remove stored reference edges whose evidence comes from the changed file.

    Args:
        conn: SQLite connection.
        file_id: ID of the changed file.

    Returns:
        Number of reference edges removed.
    """
    cursor = conn.execute(
        "DELETE FROM edges WHERE kind = 'references' AND evidence_file_id = ?",
        (file_id,),
    )
    conn.commit()
    return cursor.rowcount


def collect_impacted_symbol_ids(conn: sqlite3.Connection, file_id: str) -> list[str]:
    """Collect all symbol IDs impacted by a file change.

    This includes:
    - Symbols declared in the file (structurally refreshed)
    - Symbols referenced by edges from this file (may be stale)

    Args:
        conn: SQLite connection.
        file_id: ID of the changed file.

    Returns:
        List of impacted symbol IDs.
    """
    # Symbols declared in the file
    cursor = conn.execute(
        "SELECT id FROM nodes WHERE file_id = ?",
        (file_id,),
    )
    declared_ids = {row["id"] for row in cursor.fetchall()}

    # Symbols referenced by edges from this file
    cursor = conn.execute(
        """
        SELECT DISTINCT to_id FROM edges
        WHERE kind = 'references' AND evidence_file_id = ?
        """,
        (file_id,),
    )
    referenced_ids = {row["to_id"] for row in cursor.fetchall()}

    # Union of all impacted symbols
    all_impacted = declared_ids | referenced_ids
    return sorted(all_impacted)
