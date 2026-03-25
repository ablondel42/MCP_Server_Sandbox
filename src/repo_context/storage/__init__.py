"""Storage layer for SQLite persistence."""

from repo_context.storage.db import get_connection, close_connection
from repo_context.storage.migrations import initialize_database
from repo_context.storage.repos import upsert_repo, get_repo_by_id
from repo_context.storage.files import upsert_file, upsert_files, list_files_for_repo, delete_files_not_in_set

__all__ = [
    "get_connection",
    "close_connection",
    "initialize_database",
    "upsert_repo",
    "get_repo_by_id",
    "upsert_file",
    "upsert_files",
    "list_files_for_repo",
    "delete_files_not_in_set",
]
