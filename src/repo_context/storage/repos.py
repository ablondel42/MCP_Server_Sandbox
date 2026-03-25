"""Repository persistence helpers."""

import sqlite3

from repo_context.models.repo import RepoRecord


def upsert_repo(conn: sqlite3.Connection, repo: RepoRecord) -> None:
    """Insert or update a repository record.
    
    Args:
        conn: SQLite connection.
        repo: RepoRecord to persist.
    """
    conn.execute(
        """
        INSERT INTO repos (id, root_path, name, default_language, created_at, last_indexed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            root_path = excluded.root_path,
            name = excluded.name,
            default_language = excluded.default_language,
            created_at = excluded.created_at,
            last_indexed_at = excluded.last_indexed_at
        """,
        (
            repo.id,
            repo.root_path,
            repo.name,
            repo.default_language,
            repo.created_at,
            repo.last_indexed_at,
        ),
    )


def get_repo_by_id(conn: sqlite3.Connection, repo_id: str) -> RepoRecord | None:
    """Get a repository record by ID.
    
    Args:
        conn: SQLite connection.
        repo_id: Repository ID.
        
    Returns:
        RepoRecord if found, None otherwise.
    """
    cursor = conn.execute(
        """
        SELECT id, root_path, name, default_language, created_at, last_indexed_at
        FROM repos
        WHERE id = ?
        """,
        (repo_id,),
    )
    row = cursor.fetchone()
    
    if row is None:
        return None
    
    return RepoRecord(
        id=row["id"],
        root_path=row["root_path"],
        name=row["name"],
        default_language=row["default_language"],
        created_at=row["created_at"],
        last_indexed_at=row["last_indexed_at"],
    )
