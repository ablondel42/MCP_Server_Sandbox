"""Reference refresh state persistence."""


def upsert_reference_refresh(
    conn,
    target_symbol_id: str,
    available: bool,
    last_refreshed_at: str,
    refresh_status: str | None = None,
    error_code: str | None = None,
):
    """Upsert reference refresh state for a target symbol.

    Args:
        conn: SQLite connection.
        target_symbol_id: Target symbol ID.
        available: Whether references are available.
        last_refreshed_at: ISO 8601 timestamp.
        refresh_status: Optional status message.
        error_code: Optional error code if failed.
    """
    conn.execute(
        """
        INSERT INTO reference_refresh (
            target_symbol_id, available, last_refreshed_at, refresh_status, error_code
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(target_symbol_id) DO UPDATE SET
            available = excluded.available,
            last_refreshed_at = excluded.last_refreshed_at,
            refresh_status = excluded.refresh_status,
            error_code = excluded.error_code
        """,
        (target_symbol_id, int(available), last_refreshed_at, refresh_status, error_code),
    )


def get_reference_refresh_state(conn, target_symbol_id: str) -> dict:
    """Get reference refresh state for a target symbol.

    Args:
        conn: SQLite connection.
        target_symbol_id: Target symbol ID.

    Returns:
        Refresh state dict. Never refreshed returns available=False.
    """
    row = conn.execute(
        """
        SELECT target_symbol_id, available, last_refreshed_at, refresh_status, error_code
        FROM reference_refresh
        WHERE target_symbol_id = ?
        """,
        (target_symbol_id,),
    ).fetchone()

    if not row:
        return {
            "target_symbol_id": target_symbol_id,
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
