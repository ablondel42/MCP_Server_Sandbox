"""Graph query layer tests for Phase 04."""

import tempfile
from pathlib import Path

import pytest

from repo_context.storage import (
    get_connection,
    close_connection,
    initialize_database,
    upsert_node,
    upsert_nodes,
    upsert_edge,
    upsert_edges,
)
from repo_context.graph import (
    get_symbol,
    get_symbol_by_qualified_name,
    get_parent_symbol,
    get_child_symbols,
    get_lexical_parent_symbol,
    get_lexical_child_symbols,
    get_outgoing_edges,
    get_incoming_edges,
)


@pytest.fixture
def temp_db() -> Path:
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.fixture
def initialized_db(temp_db: Path):
    """Create an initialized database with test data."""
    conn = get_connection(temp_db)
    initialize_database(conn)
    
    # Create test nodes
    nodes = [
        {
            "id": "sym:repo:test:module:mod1",
            "repo_id": "repo:test",
            "file_id": "file:mod1.py",
            "language": "python",
            "kind": "module",
            "name": "mod1",
            "qualified_name": "mod1",
            "uri": "file:///mod1.py",
            "range_json": None,
            "selection_range_json": None,
            "parent_id": None,
            "visibility_hint": "module",
            "doc_summary": "Test module",
            "content_hash": "sha256:abc",
            "semantic_hash": "sha256:def",
            "source": "python-ast",
            "confidence": 1.0,
            "payload_json": "{}",
            "scope": "module",
            "lexical_parent_id": None,
            "last_indexed_at": "2026-01-01T00:00:00Z",
        },
        {
            "id": "sym:repo:test:class:mod1.Class1",
            "repo_id": "repo:test",
            "file_id": "file:mod1.py",
            "language": "python",
            "kind": "class",
            "name": "Class1",
            "qualified_name": "mod1.Class1",
            "uri": "file:///mod1.py",
            "range_json": None,
            "selection_range_json": None,
            "parent_id": "sym:repo:test:module:mod1",
            "visibility_hint": "public",
            "doc_summary": "Test class",
            "content_hash": "sha256:ghi",
            "semantic_hash": "sha256:jkl",
            "source": "python-ast",
            "confidence": 1.0,
            "payload_json": "{}",
            "scope": "module",
            "lexical_parent_id": None,
            "last_indexed_at": "2026-01-01T00:00:00Z",
        },
        {
            "id": "sym:repo:test:function:mod1.func1",
            "repo_id": "repo:test",
            "file_id": "file:mod1.py",
            "language": "python",
            "kind": "function",
            "name": "func1",
            "qualified_name": "mod1.func1",
            "uri": "file:///mod1.py",
            "range_json": None,
            "selection_range_json": None,
            "parent_id": "sym:repo:test:module:mod1",
            "visibility_hint": "public",
            "doc_summary": "Test function",
            "content_hash": "sha256:mno",
            "semantic_hash": "sha256:pqr",
            "source": "python-ast",
            "confidence": 1.0,
            "payload_json": "{}",
            "scope": "module",
            "lexical_parent_id": None,
            "last_indexed_at": "2026-01-01T00:00:00Z",
        },
        {
            "id": "sym:repo:test:local_function:mod1.func1.inner",
            "repo_id": "repo:test",
            "file_id": "file:mod1.py",
            "language": "python",
            "kind": "local_function",
            "name": "inner",
            "qualified_name": "mod1.func1.inner",
            "uri": "file:///mod1.py",
            "range_json": None,
            "selection_range_json": None,
            "parent_id": None,
            "visibility_hint": "private_like",
            "doc_summary": "Inner function",
            "content_hash": "sha256:stu",
            "semantic_hash": "sha256:vwx",
            "source": "python-ast",
            "confidence": 1.0,
            "payload_json": "{}",
            "scope": "function",
            "lexical_parent_id": "sym:repo:test:function:mod1.func1",
            "last_indexed_at": "2026-01-01T00:00:00Z",
        },
    ]
    upsert_nodes(conn, nodes)
    
    # Create test edges
    edges = [
        {
            "id": "edge:repo:test:contains:mod1->Class1",
            "repo_id": "repo:test",
            "kind": "contains",
            "from_id": "sym:repo:test:module:mod1",
            "to_id": "sym:repo:test:class:mod1.Class1",
            "source": "python-ast",
            "confidence": 1.0,
            "evidence_file_id": "file:mod1.py",
            "evidence_uri": "file:///mod1.py",
            "evidence_range_json": None,
            "payload_json": "{}",
            "last_indexed_at": "2026-01-01T00:00:00Z",
        },
        {
            "id": "edge:repo:test:SCOPE_PARENT:inner->func1",
            "repo_id": "repo:test",
            "kind": "SCOPE_PARENT",
            "from_id": "sym:repo:test:local_function:mod1.func1.inner",
            "to_id": "sym:repo:test:function:mod1.func1",
            "source": "python-ast",
            "confidence": 1.0,
            "evidence_file_id": "file:mod1.py",
            "evidence_uri": "file:///mod1.py",
            "evidence_range_json": None,
            "payload_json": "{}",
            "last_indexed_at": "2026-01-01T00:00:00Z",
        },
    ]
    upsert_edges(conn, edges)
    
    yield conn
    close_connection(conn)


def test_get_symbol(initialized_db) -> None:
    """Test fetching a symbol by ID."""
    conn = initialized_db
    
    result = get_symbol(conn, "sym:repo:test:module:mod1")
    assert result is not None
    assert result["kind"] == "module"


def test_get_symbol_by_qualified_name(initialized_db) -> None:
    """Test fetching a symbol by qualified name."""
    conn = initialized_db
    
    result = get_symbol_by_qualified_name(conn, "repo:test", "mod1.Class1", "class")
    assert result is not None
    assert result["name"] == "Class1"


def test_get_parent_symbol_structural(initialized_db) -> None:
    """Test getting structural parent via parent_id."""
    conn = initialized_db
    
    class_node = get_symbol(conn, "sym:repo:test:class:mod1.Class1")
    parent = get_parent_symbol(conn, class_node)
    
    assert parent is not None
    assert parent["id"] == "sym:repo:test:module:mod1"


def test_get_lexical_parent_symbol(initialized_db) -> None:
    """Test getting lexical parent via lexical_parent_id."""
    conn = initialized_db
    
    inner_node = get_symbol(conn, "sym:repo:test:local_function:mod1.func1.inner")
    lexical_parent = get_lexical_parent_symbol(conn, inner_node)
    
    assert lexical_parent is not None
    assert lexical_parent["id"] == "sym:repo:test:function:mod1.func1"


def test_get_child_symbols_structural(initialized_db) -> None:
    """Test getting structural children via parent_id."""
    conn = initialized_db
    
    children = get_child_symbols(conn, "sym:repo:test:module:mod1")
    
    assert len(children) == 2
    child_ids = {c["id"] for c in children}
    assert "sym:repo:test:class:mod1.Class1" in child_ids
    assert "sym:repo:test:function:mod1.func1" in child_ids


def test_get_lexical_child_symbols(initialized_db) -> None:
    """Test getting lexical children via lexical_parent_id."""
    conn = initialized_db
    
    children = get_lexical_child_symbols(conn, "sym:repo:test:function:mod1.func1")
    
    assert len(children) == 1
    assert children[0]["id"] == "sym:repo:test:local_function:mod1.func1.inner"


def test_get_outgoing_edges(initialized_db) -> None:
    """Test getting outgoing edges from a node."""
    conn = initialized_db
    
    edges = get_outgoing_edges(conn, "sym:repo:test:module:mod1")
    
    assert len(edges) == 1
    assert edges[0]["kind"] == "contains"


def test_get_incoming_edges(initialized_db) -> None:
    """Test getting incoming edges to a node."""
    conn = initialized_db
    
    edges = get_incoming_edges(conn, "sym:repo:test:function:mod1.func1")
    
    assert len(edges) == 1
    assert edges[0]["kind"] == "SCOPE_PARENT"
