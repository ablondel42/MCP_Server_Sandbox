"""File persistence helpers."""

import sqlite3

from repo_context.models.file import FileRecord


def upsert_file(conn: sqlite3.Connection, file_record: FileRecord) -> None:
    """Insert or update a file record.
    
    Args:
        conn: SQLite connection.
        file_record: FileRecord to persist.
    """
    conn.execute(
        """
        INSERT INTO files (
            id, repo_id, file_path, uri, module_path, language,
            content_hash, size_bytes, last_modified_at, last_indexed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            repo_id = excluded.repo_id,
            file_path = excluded.file_path,
            uri = excluded.uri,
            module_path = excluded.module_path,
            language = excluded.language,
            content_hash = excluded.content_hash,
            size_bytes = excluded.size_bytes,
            last_modified_at = excluded.last_modified_at,
            last_indexed_at = excluded.last_indexed_at
        """,
        (
            file_record.id,
            file_record.repo_id,
            file_record.file_path,
            file_record.uri,
            file_record.module_path,
            file_record.language,
            file_record.content_hash,
            file_record.size_bytes,
            file_record.last_modified_at,
            file_record.last_indexed_at,
        ),
    )


def upsert_files(conn: sqlite3.Connection, file_records: list[FileRecord]) -> None:
    """Insert or update multiple file records.
    
    Args:
        conn: SQLite connection.
        file_records: List of FileRecord to persist.
    """
    for file_record in file_records:
        upsert_file(conn, file_record)


def list_files_for_repo(conn: sqlite3.Connection, repo_id: str) -> list[FileRecord]:
    """List all file records for a repository.
    
    Args:
        conn: SQLite connection.
        repo_id: Repository ID.
        
    Returns:
        List of FileRecord sorted by file_path.
    """
    cursor = conn.execute(
        """
        SELECT id, repo_id, file_path, uri, module_path, language,
               content_hash, size_bytes, last_modified_at, last_indexed_at
        FROM files
        WHERE repo_id = ?
        ORDER BY file_path
        """,
        (repo_id,),
    )
    
    return [
        FileRecord(
            id=row["id"],
            repo_id=row["repo_id"],
            file_path=row["file_path"],
            uri=row["uri"],
            module_path=row["module_path"],
            language=row["language"],
            content_hash=row["content_hash"],
            size_bytes=row["size_bytes"],
            last_modified_at=row["last_modified_at"],
            last_indexed_at=row["last_indexed_at"],
        )
        for row in cursor.fetchall()
    ]


def delete_files_not_in_set(conn: sqlite3.Connection, repo_id: str, keep_paths: set[str]) -> None:
    """Delete file records for a repository that are not in the keep set.
    
    Args:
        conn: SQLite connection.
        repo_id: Repository ID.
        keep_paths: Set of repo-relative file paths to keep.
    """
    conn.execute(
        """
        DELETE FROM files
        WHERE repo_id = ? AND file_path NOT IN ({})
        """.format(",".join("?" * len(keep_paths))),
        (repo_id, *keep_paths),
    )
