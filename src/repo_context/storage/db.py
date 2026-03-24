"""SQLite connection helpers."""

import sqlite3
from pathlib import Path


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Get a database connection.
    
    Args:
        db_path: Path to the SQLite database file.
        
    Returns:
        A SQLite connection with row_factory enabled.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def close_connection(conn: sqlite3.Connection) -> None:
    """Close a database connection.
    
    Args:
        conn: The connection to close.
    """
    conn.close()
