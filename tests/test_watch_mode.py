"""Tests for watch mode.

Tests cover:
- Event normalization
- Batch deduplication and collapse
- Incremental reindex on modify
- Create event adds file
- Delete event removes file graph
- Reference edge invalidation
- Reference availability becomes unavailable
- Parse failure keeps previous graph state
- Rename behaves as delete + create
- Ignored files are skipped
"""

import json
import tempfile
import time
import datetime
from pathlib import Path

import pytest

from repo_context.config import AppConfig
from repo_context.storage import (
    get_connection,
    close_connection,
    initialize_database,
    upsert_repo,
    upsert_files,
    replace_file_graph,
)
from repo_context.models.repo import RepoRecord
from repo_context.models.file import FileRecord
from repo_context.indexing.events import FileChangeEvent, normalize_event, _is_ignored_path, _is_supported_file
from repo_context.indexing.scheduler import EventScheduler, collapse_events
from repo_context.indexing.invalidation import (
    mark_symbols_in_file_stale,
    invalidate_reference_summaries_for_file,
    collect_impacted_symbol_ids,
)
from repo_context.indexing.incremental import reindex_changed_file, handle_deleted_file, process_event_batch


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
def initialized_conn(temp_db_path: Path):
    """Create an initialized database connection."""
    conn = get_connection(temp_db_path)
    initialize_database(conn)
    return conn, temp_db_path


@pytest.fixture
def config():
    """Create default app config."""
    return AppConfig()


@pytest.fixture
def test_repo(tmp_path: Path):
    """Create a test repository with a Python file."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    src = repo / "src"
    src.mkdir()
    
    # Create a simple Python file
    py_file = src / "module.py"
    py_file.write_text("""
def hello():
    print("hello")

class Greeter:
    def greet(self):
        return "hi"
""")
    return repo


def _create_test_graph(conn, repo_id: str = "repo:test", file_path: str = "src/module.py"):
    """Create a minimal test graph with a file and symbols."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    repo = RepoRecord(id=repo_id, root_path="/test", name="test", default_language="python", created_at=now)
    upsert_repo(conn, repo)

    now_str = "2024-01-01T00:00:00Z"
    file_record = FileRecord(
        id=f"file:{file_path}",
        repo_id=repo_id,
        file_path=file_path,
        uri=f"file:///test/{file_path}",
        module_path=file_path.replace("/", ".").replace(".py", ""),
        language="python",
        content_hash="sha256:abc123",
        size_bytes=1000,
        last_modified_at=now_str,
    )
    upsert_files(conn, [file_record])

    # Create symbols
    symbols = [
        {
            "id": f"sym:{repo_id}:function:{file_path.replace('/', '.').replace('.py', '')}.hello",
            "repo_id": repo_id,
            "file_id": file_record.id,
            "language": "python",
            "kind": "function",
            "name": "hello",
            "qualified_name": f"{file_path.replace('/', '.').replace('.py', '')}.hello",
            "uri": f"file:///test/{file_path}",
            "range_json": json.dumps({"start": {"line": 0, "character": 0}, "end": {"line": 2, "character": 0}}),
            "selection_range_json": json.dumps({"start": {"line": 0, "character": 4}, "end": {"line": 0, "character": 9}}),
            "parent_id": f"sym:{repo_id}:module:{file_path.replace('/', '.').replace('.py', '')}",
            "visibility_hint": "public",
            "doc_summary": None,
            "content_hash": "sha256:abc",
            "semantic_hash": "sha256:abc",
            "source": "python-ast",
            "confidence": 1.0,
            "payload_json": json.dumps({"file_path": file_path, "module_path": file_path.replace("/", ".").replace(".py", "")}),
            "scope": "module",
            "lexical_parent_id": None,
            "last_indexed_at": now_str,
        },
        {
            "id": f"sym:{repo_id}:module:{file_path.replace('/', '.').replace('.py', '')}",
            "repo_id": repo_id,
            "file_id": file_record.id,
            "language": "python",
            "kind": "module",
            "name": "module",
            "qualified_name": file_path.replace("/", ".").replace(".py", ""),
            "uri": f"file:///test/{file_path}",
            "range_json": json.dumps({"start": {"line": 0, "character": 0}, "end": {"line": 100, "character": 0}}),
            "selection_range_json": json.dumps({"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}}),
            "parent_id": None,
            "visibility_hint": "public",
            "doc_summary": None,
            "content_hash": "sha256:abc123",
            "semantic_hash": "sha256:abc123",
            "source": "python-ast",
            "confidence": 1.0,
            "payload_json": json.dumps({"file_path": file_path, "module_path": file_path.replace("/", ".").replace(".py", "")}),
            "scope": "module",
            "lexical_parent_id": None,
            "last_indexed_at": now_str,
        },
    ]

    for symbol in symbols:
        conn.execute(
            """
            INSERT INTO nodes (
                id, repo_id, file_id, language, kind, name, qualified_name, uri,
                range_json, selection_range_json, parent_id, visibility_hint,
                doc_summary, content_hash, semantic_hash, source, confidence,
                payload_json, scope, lexical_parent_id, last_indexed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol["id"], symbol["repo_id"], symbol["file_id"], symbol["language"],
                symbol["kind"], symbol["name"], symbol["qualified_name"], symbol["uri"],
                symbol["range_json"], symbol["selection_range_json"], symbol["parent_id"],
                symbol["visibility_hint"], symbol["doc_summary"], symbol["content_hash"],
                symbol["semantic_hash"], symbol["source"], symbol["confidence"],
                symbol["payload_json"], symbol["scope"], symbol["lexical_parent_id"],
                symbol["last_indexed_at"],
            ),
        )

    conn.commit()
    return file_record.id


# ==================== Event Normalization Tests ====================

def test_is_ignored_path_ignores_git():
    """Test that .git paths are ignored."""
    assert _is_ignored_path(".git/config", (".git",)) is True
    assert _is_ignored_path("src/.git/HEAD", (".git",)) is True


def test_is_ignored_path_ignores_venv():
    """Test that .venv paths are ignored."""
    assert _is_ignored_path(".venv/lib/python.py", (".venv",)) is True


def test_is_ignored_path_allows_normal():
    """Test that normal paths are not ignored."""
    assert _is_ignored_path("src/module.py", (".git", ".venv")) is False


def test_is_ignored_path_ignores_dotfiles():
    """Test that dotfiles are ignored."""
    assert _is_ignored_path(".hidden.py", ()) is True


def test_is_supported_file_py():
    """Test that .py files are supported."""
    assert _is_supported_file("src/module.py", (".py",)) is True


def test_is_supported_file_js():
    """Test that .js files are not supported when only .py is configured."""
    assert _is_supported_file("src/app.js", (".py",)) is False


# ==================== Scheduler Tests ====================

def test_event_batch_deduplicates_paths():
    """Test that repeated events for same path collapse to one operation."""
    events = [
        FileChangeEvent("modified", "/test/src/a.py", "src/a.py", True),
        FileChangeEvent("modified", "/test/src/a.py", "src/a.py", True),
        FileChangeEvent("modified", "/test/src/a.py", "src/a.py", True),
    ]
    collapsed = collapse_events(events)
    assert len(collapsed) == 1
    assert collapsed[0].repo_relative_path == "src/a.py"


def test_collapse_created_then_modified():
    """Test that created + modified collapses to created."""
    events = [
        FileChangeEvent("created", "/test/src/a.py", "src/a.py", True),
        FileChangeEvent("modified", "/test/src/a.py", "src/a.py", True),
    ]
    collapsed = collapse_events(events)
    assert len(collapsed) == 1
    assert collapsed[0].event_type == "created"


def test_collapse_deleted_wins():
    """Test that deleted wins over earlier create or modify."""
    events = [
        FileChangeEvent("created", "/test/src/a.py", "src/a.py", True),
        FileChangeEvent("modified", "/test/src/a.py", "src/a.py", True),
        FileChangeEvent("deleted", "/test/src/a.py", "src/a.py", True),
    ]
    collapsed = collapse_events(events)
    assert len(collapsed) == 1
    assert collapsed[0].event_type == "deleted"


def test_scheduler_debounce():
    """Test that scheduler debounces events."""
    batches = []
    
    def on_batch(batch):
        batches.append(batch)
    
    scheduler = EventScheduler(debounce_ms=100, on_batch_ready=on_batch)
    
    # Submit events quickly
    scheduler.submit(FileChangeEvent("modified", "/test/a.py", "a.py", True))
    scheduler.submit(FileChangeEvent("modified", "/test/a.py", "a.py", True))
    scheduler.submit(FileChangeEvent("modified", "/test/a.py", "a.py", True))
    
    # Wait for debounce
    time.sleep(0.2)
    scheduler.stop()
    
    # Should have emitted one batch
    assert len(batches) == 1
    assert len(batches[0]) == 1


# ==================== Incremental Reindex Tests ====================

def test_modify_event_reindexes_file(initialized_conn, test_repo, config):
    """Test that modifying a .py file reindexes it."""
    conn, db_path = initialized_conn
    _create_test_graph(conn)
    
    # Modify the file
    py_file = test_repo / "src" / "module.py"
    py_file.write_text("""
def hello():
    print("hello world")

def goodbye():
    print("goodbye")
""")
    
    result = reindex_changed_file(conn, test_repo, str(py_file), config)
    
    assert result["status"] == "reindexed"
    assert result["node_count"] > 0
    assert result["edge_count"] > 0


def test_create_event_adds_file(initialized_conn, test_repo, config):
    """Test that creating a new .py file adds it to the graph."""
    conn, db_path = initialized_conn
    
    # Create a new file
    new_file = test_repo / "src" / "new_module.py"
    new_file.write_text("""
def new_func():
    pass
""")
    
    result = reindex_changed_file(conn, test_repo, str(new_file), config)
    
    assert result["status"] == "reindexed"
    assert result["node_count"] > 0


def test_delete_event_removes_file_graph(initialized_conn, test_repo, config):
    """Test that deleting a file removes its graph state."""
    conn, db_path = initialized_conn
    
    repo_id = f"repo:{test_repo.name}"
    file_id = _create_test_graph(conn, repo_id=repo_id, file_path="src/module.py")
    
    result = handle_deleted_file(conn, repo_id, "src/module.py")
    
    assert result["status"] == "deleted"
    assert result["deleted_node_count"] > 0
    assert result["deleted_edge_count"] >= 0
    
    # Verify file is gone
    cursor = conn.execute("SELECT COUNT(*) FROM files WHERE id = ?", (file_id,))
    assert cursor.fetchone()[0] == 0


def test_delete_not_tracked(initialized_conn):
    """Test deleting a non-tracked file returns not_tracked."""
    conn, db_path = initialized_conn
    
    result = handle_deleted_file(conn, "repo:test", "src/nonexistent.py")
    
    assert result["status"] == "not_tracked"


# ==================== Reference Invalidation Tests ====================

def test_reference_edges_for_changed_file_are_invalidated(initialized_conn):
    """Test that reference edges with matching evidence_file_id are removed."""
    conn, db_path = initialized_conn
    file_id = _create_test_graph(conn)
    
    # Add a reference edge
    conn.execute(
        """
        INSERT INTO edges (id, repo_id, kind, from_id, to_id, source, confidence,
                          evidence_file_id, evidence_uri, evidence_range_json, payload_json, last_indexed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "edge:test:references:ref1",
            "repo:test",
            "references",
            "sym:repo:test:function:other.func",
            "sym:repo:test:function:src.module.hello",
            "lsp",
            0.9,
            file_id,
            "file:///test/src/module.py",
            json.dumps({"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 5}}),
            json.dumps({"mapping_mode": "exact"}),
            "2024-01-01T00:00:00Z",
        ),
    )
    conn.commit()
    
    # Invalidate
    deleted = invalidate_reference_summaries_for_file(conn, file_id)
    
    assert deleted == 1
    
    # Verify edge is gone
    cursor = conn.execute(
        "SELECT COUNT(*) FROM edges WHERE kind = 'references' AND evidence_file_id = ?",
        (file_id,),
    )
    assert cursor.fetchone()[0] == 0


def test_reference_availability_becomes_unavailable_after_invalidation(initialized_conn):
    """Test that invalidated symbols report unavailable."""
    conn, db_path = initialized_conn
    file_id = _create_test_graph(conn)
    
    # Mark some symbols as available
    conn.execute(
        """
        INSERT INTO reference_refresh (target_symbol_id, available, last_refreshed_at)
        VALUES (?, 1, '2024-01-01T00:00:00Z')
        """,
        (f"sym:repo:test:function:src.module.hello",),
    )
    conn.commit()
    
    # Invalidate
    mark_symbols_in_file_stale(conn, file_id)
    conn.commit()
    
    # Verify availability is now 0
    cursor = conn.execute(
        "SELECT available FROM reference_refresh WHERE target_symbol_id = ?",
        (f"sym:repo:test:function:src.module.hello",),
    )
    row = cursor.fetchone()
    assert row is not None
    assert row["available"] == 0


# ==================== Parse Failure Tests ====================

def test_parse_failure_keeps_previous_graph_state(initialized_conn, test_repo, config):
    """Test that temporary broken code doesn't erase previous valid nodes."""
    conn, db_path = initialized_conn
    _create_test_graph(conn)
    
    # Count nodes before
    cursor = conn.execute("SELECT COUNT(*) FROM nodes WHERE file_id = 'file:src/module.py'")
    nodes_before = cursor.fetchone()[0]
    assert nodes_before > 0
    
    # Write broken Python file
    py_file = test_repo / "src" / "module.py"
    py_file.write_text("""
def broken(:
    this is not valid python
""")
    
    result = reindex_changed_file(conn, test_repo, str(py_file), config)
    
    assert result["status"] == "parse_failed"
    
    # Verify previous graph state is preserved
    cursor = conn.execute("SELECT COUNT(*) FROM nodes WHERE file_id = 'file:src/module.py'")
    nodes_after = cursor.fetchone()[0]
    assert nodes_after == nodes_before


# ==================== Batch Processing Tests ====================

def test_process_event_batch_reindexes(initialized_conn, test_repo, config):
    """Test that process_event_batch reindexes files."""
    conn, db_path = initialized_conn
    
    # Create a new file
    new_file = test_repo / "src" / "batch_test.py"
    new_file.write_text("""
def batch_func():
    pass
""")
    
    events = [
        FileChangeEvent("created", str(new_file), "src/batch_test.py", True),
    ]
    
    results = process_event_batch(conn, test_repo, events, config)
    
    assert len(results) == 1
    assert results[0]["status"] == "reindexed"
    assert results[0]["node_count"] > 0


def test_process_event_batch_deletes(initialized_conn, test_repo, config):
    """Test that process_event_batch handles deletes."""
    conn, db_path = initialized_conn
    repo_id = f"repo:{test_repo.name}"
    _create_test_graph(conn, repo_id=repo_id, file_path="src/module.py")
    
    events = [
        FileChangeEvent("deleted", str(test_repo / "src" / "module.py"), "src/module.py", True),
    ]
    
    results = process_event_batch(conn, test_repo, events, config)
    
    assert len(results) == 1
    assert results[0]["status"] == "deleted"


# ==================== Rename Tests ====================

def test_rename_behaves_as_delete_plus_create(initialized_conn, test_repo, config):
    """Test that rename is modeled as delete + create."""
    conn, db_path = initialized_conn
    repo_id = f"repo:{test_repo.name}"
    _create_test_graph(conn, repo_id=repo_id, file_path="src/module.py")
    
    # Create the new file in the test repo
    new_file = test_repo / "src" / "renamed.py"
    new_file.write_text("""
def renamed_func():
    pass
""")
    
    # Rename events: delete old, create new
    events = [
        FileChangeEvent("deleted", str(test_repo / "src" / "module.py"), "src/module.py", True),
        FileChangeEvent("created", str(new_file), "src/renamed.py", True),
    ]
    
    results = process_event_batch(conn, test_repo, events, config)
    
    assert len(results) == 2
    statuses = {r["status"] for r in results}
    assert "deleted" in statuses
