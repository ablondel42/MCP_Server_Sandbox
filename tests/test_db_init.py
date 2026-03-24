"""Database initialization tests."""

import tempfile
from pathlib import Path

import pytest

from repo_context.storage import get_connection, close_connection, initialize_database


@pytest.fixture
def temp_db_path() -> Path:
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


def test_initialize_database_creates_tables(temp_db_path: Path) -> None:
    """Test that initialize_database creates all required tables."""
    conn = get_connection(temp_db_path)
    try:
        initialize_database(conn)

        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {"repos", "files", "nodes", "edges", "index_runs"}
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"
    finally:
        close_connection(conn)


def test_initialize_database_creates_indexes(temp_db_path: Path) -> None:
    """Test that initialize_database creates all required indexes."""
    conn = get_connection(temp_db_path)
    try:
        initialize_database(conn)

        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
        )
        indexes = {row[0] for row in cursor.fetchall()}

        expected_indexes = {
            "idx_nodes_repo_id",
            "idx_nodes_file_id",
            "idx_nodes_qualified_name",
            "idx_nodes_parent_id",
            "idx_nodes_kind",
            "idx_edges_repo_id",
            "idx_edges_from_id",
            "idx_edges_to_id",
            "idx_edges_kind",
            "idx_edges_evidence_file_id",
            "idx_files_repo_id",
            "idx_index_runs_repo_id",
            "idx_index_runs_status",
        }
        assert expected_indexes.issubset(indexes), f"Missing indexes: {expected_indexes - indexes}"
    finally:
        close_connection(conn)


def test_initialize_database_idempotent(temp_db_path: Path) -> None:
    """Test that initialize_database can be called multiple times."""
    conn = get_connection(temp_db_path)
    try:
        # Call twice - should not fail
        initialize_database(conn)
        initialize_database(conn)

        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = list(cursor.fetchall())
        assert len(tables) == 5  # repos, files, nodes, edges, index_runs
    finally:
        close_connection(conn)
