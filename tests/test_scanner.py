"""Repository scanner tests."""

import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from repo_context.config import AppConfig
from repo_context.parsing.pathing import (
    normalize_repo_root,
    to_relative_path,
    to_file_uri,
    derive_module_path,
)
from repo_context.parsing.hashing import sha256_text, sha256_file
from repo_context.parsing.scanner import (
    should_ignore_dir,
    is_supported_source_file,
    build_repo_record,
    build_file_record,
    scan_repository,
)
from repo_context.storage import (
    get_connection,
    close_connection,
    initialize_database,
    upsert_repo,
    upsert_files,
    list_files_for_repo,
    get_repo_by_id,
)


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_repo(temp_dir: Path) -> Path:
    """Create a sample repository structure for testing."""
    repo = temp_dir / "test_repo"
    repo.mkdir()
    
    # Create app/services/auth.py
    (repo / "app").mkdir()
    (repo / "app" / "services").mkdir()
    (repo / "app" / "services" / "auth.py").write_text("def login(): pass\n")
    
    # Create app/__init__.py
    (repo / "app" / "__init__.py").write_text("")
    
    # Create main.py
    (repo / "main.py").write_text("from app import services\n")
    
    # Create ignored directories
    (repo / ".git").mkdir()
    (repo / ".git" / "config").write_text("[core]\n")
    
    (repo / "__pycache__").mkdir()
    (repo / "__pycache__" / "cache.pyc").write_text("cache")
    
    (repo / "node_modules").mkdir()
    (repo / "node_modules" / "package.js").write_text("module.exports = {}")
    
    # Create non-Python files
    (repo / "README.md").write_text("# Test Repo")
    (repo / "config.json").write_text("{}")
    
    return repo


def test_scanner_basic(sample_repo: Path) -> None:
    """Test basic scanner functionality."""
    config = AppConfig()
    repo, file_records = scan_repository(sample_repo, config)
    
    # Verify only .py files are found
    assert len(file_records) == 3
    
    # Verify file_path values are repo-relative
    paths = [f.file_path for f in file_records]
    assert "app/__init__.py" in paths
    assert "app/services/auth.py" in paths
    assert "main.py" in paths
    
    # Verify results are sorted deterministically
    assert paths == sorted(paths)
    
    # Verify module_path values are correct
    modules = {f.file_path: f.module_path for f in file_records}
    assert modules["app/__init__.py"] == "app"
    assert modules["app/services/auth.py"] == "app.services.auth"
    assert modules["main.py"] == "main"


def test_scanner_ignores_dirs(sample_repo: Path) -> None:
    """Test that ignored directories are skipped."""
    config = AppConfig()
    repo, file_records = scan_repository(sample_repo, config)
    
    # Verify no files from ignored directories
    all_paths = [f.file_path for f in file_records]
    for path in all_paths:
        assert not path.startswith(".git/")
        assert not path.startswith("__pycache__/")
        assert not path.startswith("node_modules/")


def test_module_path_derivation(temp_dir: Path) -> None:
    """Test module path derivation with exact mappings from spec."""
    repo = temp_dir / "test_repo"
    repo.mkdir()
    
    # Create test files
    (repo / "app").mkdir()
    (repo / "app" / "services").mkdir()
    (repo / "app" / "services" / "auth.py").write_text("")
    (repo / "app" / "__init__.py").write_text("")
    
    (repo / "pkg").mkdir()
    (repo / "pkg" / "subpkg").mkdir()
    (repo / "pkg" / "subpkg" / "__init__.py").write_text("")
    
    (repo / "main.py").write_text("")
    
    (repo / "tools").mkdir()
    (repo / "tools" / "_internal.py").write_text("")
    
    # Test exact mappings from spec
    assert derive_module_path(repo, repo / "app" / "services" / "auth.py") == "app.services.auth"
    assert derive_module_path(repo, repo / "app" / "__init__.py") == "app"
    assert derive_module_path(repo, repo / "pkg" / "subpkg" / "__init__.py") == "pkg.subpkg"
    assert derive_module_path(repo, repo / "main.py") == "main"
    assert derive_module_path(repo, repo / "tools" / "_internal.py") == "tools._internal"


def test_file_uri_generation(temp_dir: Path) -> None:
    """Test file URI generation."""
    repo = temp_dir / "test_repo"
    repo.mkdir()
    test_file = repo / "test.py"
    test_file.write_text("")
    
    uri = to_file_uri(test_file)
    
    # Verify URI begins with file://
    assert uri.startswith("file://")
    
    # Verify it's a valid URI
    from urllib.parse import urlparse
    parsed = urlparse(uri)
    assert parsed.scheme == "file"


def test_hashing_is_stable(temp_dir: Path) -> None:
    """Test that hashing is stable and uses sha256: prefix."""
    test_file = temp_dir / "test.py"
    test_file.write_text("test content")
    
    # Hash twice
    hash1 = sha256_file(test_file)
    hash2 = sha256_file(test_file)
    
    # Verify same hash returned
    assert hash1 == hash2
    
    # Verify sha256: prefix
    assert hash1.startswith("sha256:")
    assert hash2.startswith("sha256:")


def test_scan_persists_records(sample_repo: Path, temp_dir: Path) -> None:
    """Test that scanning persists records to database."""
    db_path = temp_dir / "test.db"
    config = AppConfig()
    
    # Initialize database
    conn = get_connection(db_path)
    initialize_database(conn)
    
    # Scan and persist
    repo, file_records = scan_repository(sample_repo, config)
    upsert_repo(conn, repo)
    upsert_files(conn, file_records)
    conn.commit()
    
    # Verify one repo row exists
    stored_repo = get_repo_by_id(conn, repo.id)
    assert stored_repo is not None
    
    # Verify expected file rows exist
    stored_files = list_files_for_repo(conn, repo.id)
    assert len(stored_files) == 3
    
    close_connection(conn)


def test_empty_repo(temp_dir: Path) -> None:
    """Test scanning a repo with no .py files."""
    repo = temp_dir / "empty_repo"
    repo.mkdir()
    
    # Add non-Python files only
    (repo / "README.md").write_text("# Empty")
    (repo / "config.json").write_text("{}")
    
    config = AppConfig()
    repo_record, file_records = scan_repository(repo, config)
    
    # Verify no crash
    assert repo_record is not None
    
    # Verify repo row would exist
    assert repo_record.id.startswith("repo:")
    
    # Verify file count is zero
    assert len(file_records) == 0


def test_invalid_repo_path(temp_dir: Path) -> None:
    """Test that invalid repo paths fail clearly."""
    config = AppConfig()
    
    # Test non-existent path
    non_existent = temp_dir / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        scan_repository(non_existent, config)
    
    # Test non-directory path
    file_path = temp_dir / "not_a_dir.txt"
    file_path.write_text("content")
    with pytest.raises(NotADirectoryError):
        scan_repository(file_path, config)


def test_should_ignore_dir() -> None:
    """Test directory ignore matching."""
    ignored_dirs = (".git", "__pycache__", "node_modules")
    
    # Verify exact matching
    assert should_ignore_dir(".git", ignored_dirs) is True
    assert should_ignore_dir("__pycache__", ignored_dirs) is True
    assert should_ignore_dir("node_modules", ignored_dirs) is True
    
    # Verify non-matches
    assert should_ignore_dir("src", ignored_dirs) is False
    assert should_ignore_dir(".github", ignored_dirs) is False  # Not exact match


def test_is_supported_source_file() -> None:
    """Test supported file extension filtering."""
    supported_extensions = (".py",)
    
    # Verify .py files are supported
    assert is_supported_source_file(Path("test.py"), supported_extensions) is True
    
    # Verify non-.py files are not supported
    assert is_supported_source_file(Path("test.txt"), supported_extensions) is False
    assert is_supported_source_file(Path("test.md"), supported_extensions) is False
    assert is_supported_source_file(Path("test.json"), supported_extensions) is False


def test_build_repo_record(temp_dir: Path) -> None:
    """Test repo record building."""
    repo_root = temp_dir / "my_project"
    repo_root.mkdir()
    
    repo = build_repo_record(repo_root)
    
    assert repo.id == "repo:my_project"
    assert repo.name == "my_project"
    assert repo.default_language == "python"
    assert repo.root_path == str(repo_root)
    assert repo.created_at is not None
    assert repo.last_indexed_at is not None


def test_build_file_record(temp_dir: Path) -> None:
    """Test file record building with all fields."""
    repo = temp_dir / "test_repo"
    repo.mkdir()
    test_file = repo / "test.py"
    test_file.write_text("test content")
    
    repo_id = "repo:test_repo"
    record = build_file_record(repo_id, repo, test_file)
    
    # Verify all fields are populated
    assert record.id == "file:test.py"
    assert record.repo_id == repo_id
    assert record.file_path == "test.py"
    assert record.uri.startswith("file://")
    assert record.module_path == "test"
    assert record.language == "python"
    assert record.content_hash.startswith("sha256:")
    assert record.size_bytes > 0
    assert record.last_modified_at is not None
    assert record.last_indexed_at is not None


def test_normalize_repo_root(temp_dir: Path) -> None:
    """Test repo root normalization."""
    # Test valid directory
    result = normalize_repo_root(temp_dir)
    assert result.is_absolute()
    assert result.exists()
    
    # Test non-existent path
    with pytest.raises(FileNotFoundError):
        normalize_repo_root(temp_dir / "nonexistent")
    
    # Test non-directory
    file_path = temp_dir / "file.txt"
    file_path.write_text("content")
    with pytest.raises(NotADirectoryError):
        normalize_repo_root(file_path)


def test_to_relative_path(temp_dir: Path) -> None:
    """Test relative path conversion."""
    repo = temp_dir / "repo"
    repo.mkdir()
    subdir = repo / "subdir"
    subdir.mkdir()
    file = subdir / "test.py"
    file.write_text("")
    
    result = to_relative_path(repo, file)
    
    # Verify POSIX-style path
    assert result == "subdir/test.py"
    assert "\\" not in result


def test_sha256_text() -> None:
    """Test text hashing."""
    hash1 = sha256_text("test")
    hash2 = sha256_text("test")
    hash3 = sha256_text("different")
    
    # Verify stability
    assert hash1 == hash2
    
    # Verify different input produces different hash
    assert hash1 != hash3
    
    # Verify prefix
    assert hash1.startswith("sha256:")


def test_scan_repo_cli_command(sample_repo: Path, temp_dir: Path) -> None:
    """Test the scan-repo CLI command."""
    db_path = temp_dir / "test.db"
    
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "repo_context.cli.main",
            "scan-repo",
            str(sample_repo),
            "--db-path",
            str(db_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(temp_dir),
    )
    
    # Verify success
    assert result.returncode == 0
    assert "Repository scanned successfully" in result.stdout
    
    # Verify database was created
    assert db_path.exists()
    
    # Verify records were persisted
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM files")
    count = cursor.fetchone()[0]
    conn.close()
    
    assert count == 3  # app/__init__.py, app/services/auth.py, main.py
