"""CLI tests."""

import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

from repo_context.cli.main import main
from repo_context.storage import initialize_database


@pytest.fixture
def temp_db_path() -> Path:
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


def test_init_db_command(temp_db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test init-db command creates database with schema."""
    monkeypatch.setattr(
        "sys.argv",
        ["repo-context", "init-db", "--db-path", str(temp_db_path)],
    )

    exit_code = main()
    assert exit_code == 0
    assert temp_db_path.exists()

    # Verify schema was created
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()

    assert "repos" in tables
    assert "files" in tables
    assert "nodes" in tables
    assert "edges" in tables
    assert "index_runs" in tables


def test_doctor_command_after_init(temp_db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test doctor command passes after database initialization."""
    # First initialize the database
    conn = sqlite3.connect(temp_db_path)
    initialize_database(conn)
    conn.close()

    # Run doctor command
    monkeypatch.setattr(
        "sys.argv",
        ["repo-context", "doctor", "--db-path", str(temp_db_path)],
    )

    exit_code = main()
    assert exit_code == 0


def test_doctor_command_missing_tables(temp_db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test doctor command fails when tables are missing."""
    # Create empty database without schema
    conn = sqlite3.connect(temp_db_path)
    conn.close()

    # Run doctor command
    monkeypatch.setattr(
        "sys.argv",
        ["repo-context", "doctor", "--db-path", str(temp_db_path)],
    )

    exit_code = main()
    assert exit_code == 1
