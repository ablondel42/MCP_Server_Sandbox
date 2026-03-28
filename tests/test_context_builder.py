"""Context builder tests for Phase 05."""

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
from repo_context.context import build_symbol_context


@pytest.fixture
def temp_db() -> Path:
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.fixture
def context_test_db(temp_db: Path):
    """Create database with context test data."""
    conn = get_connection(temp_db)
    initialize_database(conn)
    
    # Create module node
    module_node = {
        "id": "sym:repo:test:module:test_module",
        "repo_id": "repo:test",
        "file_id": "file:test_module.py",
        "language": "python",
        "kind": "module",
        "name": "test_module",
        "qualified_name": "test_module",
        "uri": "file:///test_module.py",
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
    }
    upsert_node(conn, module_node)
    
    # Create class node with structural parent = module
    class_node = {
        "id": "sym:repo:test:class:test_module.TestClass",
        "repo_id": "repo:test",
        "file_id": "file:test_module.py",
        "language": "python",
        "kind": "class",
        "name": "TestClass",
        "qualified_name": "test_module.TestClass",
        "uri": "file:///test_module.py",
        "range_json": None,
        "selection_range_json": None,
        "parent_id": "sym:repo:test:module:test_module",
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
    }
    upsert_node(conn, class_node)
    
    # Create method node with structural parent = class
    method_node = {
        "id": "sym:repo:test:method:test_module.TestClass.test_method",
        "repo_id": "repo:test",
        "file_id": "file:test_module.py",
        "language": "python",
        "kind": "method",
        "name": "test_method",
        "qualified_name": "test_module.TestClass.test_method",
        "uri": "file:///test_module.py",
        "range_json": None,
        "selection_range_json": None,
        "parent_id": "sym:repo:test:class:test_module.TestClass",
        "visibility_hint": "public",
        "doc_summary": "Test method",
        "content_hash": "sha256:mno",
        "semantic_hash": "sha256:pqr",
        "source": "python-ast",
        "confidence": 1.0,
        "payload_json": "{}",
        "scope": "class",
        "lexical_parent_id": "sym:repo:test:class:test_module.TestClass",
        "last_indexed_at": "2026-01-01T00:00:00Z",
    }
    upsert_node(conn, method_node)
    
    # Create local function with lexical parent
    local_func_node = {
        "id": "sym:repo:test:local_function:test_module.outer.inner",
        "repo_id": "repo:test",
        "file_id": "file:test_module.py",
        "language": "python",
        "kind": "local_function",
        "name": "inner",
        "qualified_name": "test_module.outer.inner",
        "uri": "file:///test_module.py",
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
        "lexical_parent_id": "sym:repo:test:function:test_module.outer",
        "last_indexed_at": "2026-01-01T00:00:00Z",
    }
    upsert_node(conn, local_func_node)
    
    # Create outer function
    outer_func_node = {
        "id": "sym:repo:test:function:test_module.outer",
        "repo_id": "repo:test",
        "file_id": "file:test_module.py",
        "language": "python",
        "kind": "function",
        "name": "outer",
        "qualified_name": "test_module.outer",
        "uri": "file:///test_module.py",
        "range_json": None,
        "selection_range_json": None,
        "parent_id": "sym:repo:test:module:test_module",
        "visibility_hint": "public",
        "doc_summary": "Outer function",
        "content_hash": "sha256:yza",
        "semantic_hash": "sha256:bcd",
        "source": "python-ast",
        "confidence": 1.0,
        "payload_json": "{}",
        "scope": "module",
        "lexical_parent_id": None,
        "last_indexed_at": "2026-01-01T00:00:00Z",
    }
    upsert_node(conn, outer_func_node)
    
    # Create factory function for local class test
    factory_func_node = {
        "id": "sym:repo:test:function:test_module.factory",
        "repo_id": "repo:test",
        "file_id": "file:test_module.py",
        "language": "python",
        "kind": "function",
        "name": "factory",
        "qualified_name": "test_module.factory",
        "uri": "file:///test_module.py",
        "range_json": None,
        "selection_range_json": None,
        "parent_id": "sym:repo:test:module:test_module",
        "visibility_hint": "public",
        "doc_summary": "Factory function",
        "content_hash": "sha256:klm",
        "semantic_hash": "sha256:nop",
        "source": "python-ast",
        "confidence": 1.0,
        "payload_json": "{}",
        "scope": "module",
        "lexical_parent_id": None,
        "last_indexed_at": "2026-01-01T00:00:00Z",
    }
    upsert_node(conn, factory_func_node)
    
    # Create local class with scope=function
    local_class_node = {
        "id": "sym:repo:test:class:test_module.factory.LocalClass",
        "repo_id": "repo:test",
        "file_id": "file:test_module.py",
        "language": "python",
        "kind": "class",
        "name": "LocalClass",
        "qualified_name": "test_module.factory.LocalClass",
        "uri": "file:///test_module.py",
        "range_json": None,
        "selection_range_json": None,
        "parent_id": None,
        "visibility_hint": "public",
        "doc_summary": "Local class",
        "content_hash": "sha256:efg",
        "semantic_hash": "sha256:hij",
        "source": "python-ast",
        "confidence": 1.0,
        "payload_json": "{}",
        "scope": "function",
        "lexical_parent_id": "sym:repo:test:function:test_module.factory",
        "last_indexed_at": "2026-01-01T00:00:00Z",
    }
    upsert_node(conn, local_class_node)
    
    # Create contains edge
    contains_edge = {
        "id": "edge:repo:test:contains:module->class",
        "repo_id": "repo:test",
        "kind": "contains",
        "from_id": "sym:repo:test:module:test_module",
        "to_id": "sym:repo:test:class:test_module.TestClass",
        "source": "python-ast",
        "confidence": 1.0,
        "evidence_file_id": "file:test_module.py",
        "evidence_uri": "file:///test_module.py",
        "evidence_range_json": None,
        "payload_json": "{}",
        "last_indexed_at": "2026-01-01T00:00:00Z",
    }
    upsert_edge(conn, contains_edge)
    
    # Create SCOPE_PARENT edge
    scope_edge = {
        "id": "edge:repo:test:SCOPE_PARENT:inner->outer",
        "repo_id": "repo:test",
        "kind": "SCOPE_PARENT",
        "from_id": "sym:repo:test:local_function:test_module.outer.inner",
        "to_id": "sym:repo:test:function:test_module.outer",
        "source": "python-ast",
        "confidence": 1.0,
        "evidence_file_id": "file:test_module.py",
        "evidence_uri": "file:///test_module.py",
        "evidence_range_json": None,
        "payload_json": "{}",
        "last_indexed_at": "2026-01-01T00:00:00Z",
    }
    upsert_edge(conn, scope_edge)
    
    # Create import edge with placeholder target
    import_edge = {
        "id": "edge:repo:test:imports:module->external",
        "repo_id": "repo:test",
        "kind": "imports",
        "from_id": "sym:repo:test:module:test_module",
        "to_id": "external_or_unresolved:external_module",
        "source": "python-ast",
        "confidence": 0.8,
        "evidence_file_id": "file:test_module.py",
        "evidence_uri": "file:///test_module.py",
        "evidence_range_json": None,
        "payload_json": "{}",
        "last_indexed_at": "2026-01-01T00:00:00Z",
    }
    upsert_edge(conn, import_edge)
    
    yield conn
    close_connection(conn)


def test_build_symbol_context_for_module_function(context_test_db) -> None:
    """Test context for module-level function."""
    conn = context_test_db
    
    context = build_symbol_context(conn, "sym:repo:test:function:test_module.outer")
    
    assert context is not None
    assert context.focus_symbol["kind"] == "function"
    assert context.focus_symbol["scope"] == "module"
    # Structural parent should be module
    assert context.structural_parent is not None
    assert context.structural_parent["kind"] == "module"
    # Lexical parent should be None for module-level function
    assert context.lexical_parent is None


def test_build_symbol_context_for_method(context_test_db) -> None:
    """Test context for method."""
    conn = context_test_db
    
    context = build_symbol_context(conn, "sym:repo:test:method:test_module.TestClass.test_method")
    
    assert context is not None
    assert context.focus_symbol["kind"] == "method"
    # Structural parent should be class
    assert context.structural_parent is not None
    assert context.structural_parent["kind"] == "class"
    # Lexical parent should also be class for method
    assert context.lexical_parent is not None
    assert context.lexical_parent["kind"] == "class"


def test_build_symbol_context_for_local_function(context_test_db) -> None:
    """Test context for local function."""
    conn = context_test_db
    
    context = build_symbol_context(conn, "sym:repo:test:local_function:test_module.outer.inner")
    
    assert context is not None
    assert context.focus_symbol["kind"] == "local_function"
    assert context.focus_symbol["scope"] == "function"
    # Lexical parent should be outer function
    assert context.lexical_parent is not None
    assert context.lexical_parent["kind"] == "function"
    # Lexical children should be empty (no nested functions inside inner)
    assert len(context.lexical_children) == 0


def test_build_symbol_context_for_local_class(context_test_db) -> None:
    """Test context for local class."""
    conn = context_test_db
    
    context = build_symbol_context(conn, "sym:repo:test:class:test_module.factory.LocalClass")
    
    assert context is not None
    assert context.focus_symbol["kind"] == "class"
    assert context.focus_symbol["scope"] == "function"
    # Lexical parent should be factory function
    assert context.lexical_parent is not None
    assert context.lexical_parent["kind"] == "function"


def test_structural_and_lexical_parents_are_distinct(context_test_db) -> None:
    """Test that structural and lexical parents remain separate."""
    conn = context_test_db
    
    # For method, both should point to class but are separate fields
    context = build_symbol_context(conn, "sym:repo:test:method:test_module.TestClass.test_method")
    
    assert context is not None
    # Both fields exist and are accessible
    assert hasattr(context, "structural_parent")
    assert hasattr(context, "lexical_parent")
    # For method, both happen to be the class
    assert context.structural_parent is not None
    assert context.lexical_parent is not None


def test_file_siblings_are_deterministic(context_test_db) -> None:
    """Test that file siblings are ordered deterministically."""
    conn = context_test_db
    
    context1 = build_symbol_context(conn, "sym:repo:test:module:test_module")
    context2 = build_symbol_context(conn, "sym:repo:test:module:test_module")
    
    assert context1 is not None
    assert context2 is not None
    
    # Siblings should be identical across calls
    assert len(context1.file_siblings) == len(context2.file_siblings)
    for i, sib in enumerate(context1.file_siblings):
        assert sib["id"] == context2.file_siblings[i]["id"]
        assert sib["qualified_name"] == context2.file_siblings[i]["qualified_name"]


def test_context_handles_placeholder_targets(context_test_db) -> None:
    """Test that placeholder targets don't break context."""
    conn = context_test_db
    
    context = build_symbol_context(conn, "sym:repo:test:module:test_module")
    
    assert context is not None
    # Should have import edge with placeholder target
    assert context.confidence["contains_placeholder_targets"] is True
    # Context assembly should not crash


def test_structural_summary_flags_local_declarations(context_test_db) -> None:
    """Test structural summary flags for local declarations."""
    conn = context_test_db
    
    # Test local function
    context = build_symbol_context(conn, "sym:repo:test:local_function:test_module.outer.inner")
    assert context is not None
    assert context.structural_summary["is_local_declaration"] is True
    assert context.structural_summary["is_nested_declaration"] is True
    
    # Test local class
    context = build_symbol_context(conn, "sym:repo:test:class:test_module.factory.LocalClass")
    assert context is not None
    assert context.structural_summary["is_local_declaration"] is True
    assert context.structural_summary["is_nested_declaration"] is True
    
    # Test module-level function
    context = build_symbol_context(conn, "sym:repo:test:function:test_module.outer")
    assert context is not None
    assert context.structural_summary["is_local_declaration"] is False
    assert context.structural_summary["is_nested_declaration"] is False


def test_missing_symbol_returns_none(context_test_db) -> None:
    """Test that missing symbol returns None."""
    conn = context_test_db
    
    context = build_symbol_context(conn, "sym:repo:test:nonexistent")
    
    assert context is None


def test_end_to_end_context_flow(context_test_db) -> None:
    """End-to-end test: build context and verify all fields."""
    conn = context_test_db
    
    context = build_symbol_context(conn, "sym:repo:test:class:test_module.TestClass")
    
    assert context is not None
    
    # Verify all required fields exist
    assert context.focus_symbol is not None
    assert context.structural_parent is not None  # module
    assert isinstance(context.structural_children, list)  # methods
    assert context.lexical_parent is None  # class at module level
    assert isinstance(context.lexical_children, list)
    assert isinstance(context.incoming_edges, list)
    assert isinstance(context.outgoing_edges, list)
    assert isinstance(context.file_siblings, list)
    assert isinstance(context.structural_summary, dict)
    assert isinstance(context.freshness, dict)
    assert isinstance(context.confidence, dict)
    
    # Verify summary fields
    assert "has_structural_parent" in context.structural_summary
    assert "structural_child_count" in context.structural_summary
    assert "has_lexical_parent" in context.structural_summary
    assert "lexical_child_count" in context.structural_summary
    assert "scope" in context.structural_summary
    
    # Verify freshness fields
    assert "node_last_indexed_at" in context.freshness
    assert "context_source" in context.freshness
    assert context.freshness["context_source"] == "graph_only"
    
    # Verify confidence fields
    assert "focus_symbol_confidence" in context.confidence
    assert "graph_only" in context.confidence
    assert context.confidence["graph_only"] is True
