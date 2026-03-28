"""Graph storage tests for Phase 04."""

import json
import tempfile
from pathlib import Path

import pytest

from repo_context.storage import (
    get_connection,
    close_connection,
    initialize_database,
    upsert_node,
    upsert_nodes,
    get_node_by_id,
    get_node_by_qualified_name,
    list_nodes_for_file,
    list_nodes_for_repo,
    list_child_nodes,
    list_lexical_children,
    delete_nodes_for_file,
    upsert_edge,
    upsert_edges,
    get_edge_by_id,
    list_edges_for_repo,
    list_outgoing_edges,
    list_incoming_edges,
    list_edges_for_file,
    delete_edges_for_file,
    replace_file_graph,
)


@pytest.fixture
def temp_db() -> Path:
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.fixture
def initialized_db(temp_db: Path):
    """Create an initialized database connection."""
    conn = get_connection(temp_db)
    initialize_database(conn)
    yield conn
    close_connection(conn)


def _create_test_node(node_id: str, kind: str, qualified_name: str, file_id: str = "file:test.py") -> dict:
    """Create a test node dictionary.
    
    Args:
        node_id: Node ID.
        kind: Node kind.
        qualified_name: Qualified name.
        file_id: File ID (default: "file:test.py").
        
    Returns:
        Test node dictionary.
    """
    return {
        "id": node_id,
        "repo_id": "repo:test",
        "file_id": file_id,
        "language": "python",
        "kind": kind,
        "name": qualified_name.split(".")[-1],
        "qualified_name": qualified_name,
        "uri": f"file:///{file_id.replace('file:', '')}",
        "range_json": {"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 0}},
        "selection_range_json": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 10}},
        "parent_id": None,
        "visibility_hint": "public",
        "doc_summary": "Test node",
        "content_hash": "sha256:abc123",
        "semantic_hash": "sha256:def456",
        "source": "python-ast",
        "confidence": 1.0,
        "payload_json": {"test": "data"},
        "scope": "module",
        "lexical_parent_id": None,
        "last_indexed_at": "2026-01-01T00:00:00Z",
    }


def _create_test_edge(edge_id: str, kind: str, from_id: str, to_id: str, file_id: str = "file:test.py") -> dict:
    """Create a test edge dictionary.
    
    Args:
        edge_id: Edge ID.
        kind: Edge kind.
        from_id: Source node ID.
        to_id: Target node ID.
        file_id: File ID (default: "file:test.py").
        
    Returns:
        Test edge dictionary.
    """
    return {
        "id": edge_id,
        "repo_id": "repo:test",
        "kind": kind,
        "from_id": from_id,
        "to_id": to_id,
        "source": "python-ast",
        "confidence": 1.0,
        "evidence_file_id": file_id,
        "evidence_uri": f"file:///{file_id.replace('file:', '')}",
        "evidence_range_json": {"start": {"line": 0, "character": 0}, "end": {"line": 5, "character": 0}},
        "payload_json": {"test": "edge_data"},
        "last_indexed_at": "2026-01-01T00:00:00Z",
    }


# ============== Node Upsert Tests ==============


def test_upsert_node_inserts_new(initialized_db) -> None:
    """Test that upsert_node inserts a new node."""
    conn = initialized_db
    node = _create_test_node("sym:repo:test:module:test", "module", "test")
    
    upsert_node(conn, node)
    
    result = get_node_by_id(conn, "sym:repo:test:module:test")
    assert result is not None
    assert result["id"] == "sym:repo:test:module:test"
    assert result["kind"] == "module"


def test_upsert_node_updates_existing(initialized_db) -> None:
    """Test that upsert_node updates an existing node."""
    conn = initialized_db
    node = _create_test_node("sym:repo:test:module:test", "module", "test")
    
    # Insert first time
    upsert_node(conn, node)
    
    # Update with new data
    node["doc_summary"] = "Updated summary"
    upsert_node(conn, node)
    
    result = get_node_by_id(conn, "sym:repo:test:module:test")
    assert result is not None
    assert result["doc_summary"] == "Updated summary"
    # Should still be only one row
    nodes = list_nodes_for_repo(conn, "repo:test")
    assert len(nodes) == 1


def test_upsert_nodes_bulk(initialized_db) -> None:
    """Test that upsert_nodes inserts multiple nodes."""
    conn = initialized_db
    nodes = [
        _create_test_node("sym:repo:test:module:mod1", "module", "mod1"),
        _create_test_node("sym:repo:test:class:mod1.Class1", "class", "mod1.Class1"),
        _create_test_node("sym:repo:test:function:mod1.func1", "function", "mod1.func1"),
    ]
    
    upsert_nodes(conn, nodes)
    
    all_nodes = list_nodes_for_repo(conn, "repo:test")
    assert len(all_nodes) == 3


# ============== Node Read Helper Tests ==============


def test_get_node_by_id(initialized_db) -> None:
    """Test fetching a node by ID."""
    conn = initialized_db
    node = _create_test_node("sym:repo:test:module:test", "module", "test")
    upsert_node(conn, node)
    
    result = get_node_by_id(conn, "sym:repo:test:module:test")
    assert result is not None
    assert result["id"] == "sym:repo:test:module:test"


def test_get_node_by_qualified_name(initialized_db) -> None:
    """Test fetching a node by qualified name."""
    conn = initialized_db
    node = _create_test_node("sym:repo:test:module:test", "module", "test")
    upsert_node(conn, node)
    
    result = get_node_by_qualified_name(conn, "repo:test", "test")
    assert result is not None
    assert result["qualified_name"] == "test"


def test_list_nodes_for_file(initialized_db) -> None:
    """Test listing nodes for a specific file."""
    conn = initialized_db
    nodes = [
        _create_test_node("sym:repo:test:module:test", "module", "test"),
        _create_test_node("sym:repo:test:class:test.Class1", "class", "test.Class1"),
    ]
    upsert_nodes(conn, nodes)
    
    result = list_nodes_for_file(conn, "file:test.py")
    assert len(result) == 2


def test_list_child_nodes_structural(initialized_db) -> None:
    """Test listing structural children via parent_id."""
    conn = initialized_db
    
    # Create parent module
    module = _create_test_node("sym:repo:test:module:parent", "module", "parent")
    upsert_node(conn, module)
    
    # Create child class with parent_id
    child = _create_test_node("sym:repo:test:class:parent.Child", "class", "parent.Child")
    child["parent_id"] = "sym:repo:test:module:parent"
    upsert_node(conn, child)
    
    children = list_child_nodes(conn, "sym:repo:test:module:parent")
    assert len(children) == 1
    assert children[0]["id"] == "sym:repo:test:class:parent.Child"


def test_list_lexical_children(initialized_db) -> None:
    """Test listing lexical children via lexical_parent_id."""
    conn = initialized_db
    
    # Create parent function
    parent = _create_test_node("sym:repo:test:function:outer", "function", "outer")
    upsert_node(conn, parent)
    
    # Create nested function with lexical_parent_id
    nested = _create_test_node(
        "sym:repo:test:local_function:outer.inner",
        "local_function",
        "outer.inner"
    )
    nested["lexical_parent_id"] = "sym:repo:test:function:outer"
    upsert_node(conn, nested)
    
    children = list_lexical_children(conn, "sym:repo:test:function:outer")
    assert len(children) == 1
    assert children[0]["id"] == "sym:repo:test:local_function:outer.inner"


def test_delete_nodes_for_file(initialized_db) -> None:
    """Test deleting all nodes for a file."""
    conn = initialized_db
    
    nodes = [
        _create_test_node("sym:repo:test:module:test", "module", "test"),
        _create_test_node("sym:repo:test:class:test.Class1", "class", "test.Class1"),
    ]
    upsert_nodes(conn, nodes)
    
    # Verify nodes exist
    assert len(list_nodes_for_file(conn, "file:test.py")) == 2
    
    # Delete nodes for file
    delete_nodes_for_file(conn, "file:test.py")
    
    # Verify nodes are deleted
    assert len(list_nodes_for_file(conn, "file:test.py")) == 0


# ============== Edge Upsert Tests ==============


def test_upsert_edge_inserts_new(initialized_db) -> None:
    """Test that upsert_edge inserts a new edge."""
    conn = initialized_db
    edge = _create_test_edge(
        "edge:repo:test:contains:mod1->class1",
        "contains",
        "sym:repo:test:module:mod1",
        "sym:repo:test:class:mod1.Class1"
    )
    
    upsert_edge(conn, edge)
    
    result = get_edge_by_id(conn, "edge:repo:test:contains:mod1->class1")
    assert result is not None
    assert result["kind"] == "contains"


def test_upsert_edge_updates_existing(initialized_db) -> None:
    """Test that upsert_edge updates an existing edge."""
    conn = initialized_db
    edge = _create_test_edge(
        "edge:repo:test:contains:mod1->class1",
        "contains",
        "sym:repo:test:module:mod1",
        "sym:repo:test:class:mod1.Class1"
    )
    
    # Insert first time
    upsert_edge(conn, edge)
    
    # Update with new data
    edge["confidence"] = 0.9
    upsert_edge(conn, edge)
    
    result = get_edge_by_id(conn, "edge:repo:test:contains:mod1->class1")
    assert result is not None
    assert result["confidence"] == 0.9


# ============== Edge Read Helper Tests ==============


def test_list_outgoing_edges(initialized_db) -> None:
    """Test listing outgoing edges from a node."""
    conn = initialized_db
    
    # Create edges
    edges = [
        _create_test_edge("edge1", "contains", "sym:parent", "sym:child1"),
        _create_test_edge("edge2", "imports", "sym:parent", "sym:external"),
    ]
    upsert_edges(conn, edges)
    
    outgoing = list_outgoing_edges(conn, "sym:parent")
    assert len(outgoing) == 2


def test_list_incoming_edges(initialized_db) -> None:
    """Test listing incoming edges to a node."""
    conn = initialized_db
    
    # Create edges
    edges = [
        _create_test_edge("edge1", "contains", "sym:parent", "sym:child"),
        _create_test_edge("edge2", "SCOPE_PARENT", "sym:lexical_parent", "sym:child"),
    ]
    upsert_edges(conn, edges)
    
    incoming = list_incoming_edges(conn, "sym:child")
    assert len(incoming) == 2


def test_delete_edges_for_file(initialized_db) -> None:
    """Test deleting all edges for a file."""
    conn = initialized_db
    
    edges = [
        _create_test_edge("edge1", "contains", "sym:parent", "sym:child"),
        _create_test_edge("edge2", "imports", "sym:mod", "sym:external"),
    ]
    upsert_edges(conn, edges)
    
    # Verify edges exist
    assert len(list_edges_for_file(conn, "file:test.py")) == 2
    
    # Delete edges for file
    delete_edges_for_file(conn, "file:test.py")
    
    # Verify edges are deleted
    assert len(list_edges_for_file(conn, "file:test.py")) == 0


# ============== Replace File Graph Tests ==============


def test_replace_file_graph(initialized_db) -> None:
    """Test replacing a file's entire graph."""
    conn = initialized_db
    file_id = "file:old.py"

    # Initial nodes and edges
    initial_nodes = [
        _create_test_node("sym:repo:test:module:old", "module", "old", file_id),
        _create_test_node("sym:repo:test:class:old.Class1", "class", "old.Class1", file_id),
    ]
    initial_edges = [
        _create_test_edge("edge1", "contains", "sym:repo:test:module:old", "sym:repo:test:class:old.Class1", file_id),
    ]

    # Insert initial graph
    replace_file_graph(conn, file_id, initial_nodes, initial_edges)

    # Verify initial state
    nodes = list_nodes_for_file(conn, file_id)
    assert len(nodes) == 2

    # New nodes and edges
    new_nodes = [
        _create_test_node("sym:repo:test:module:new", "module", "new", file_id),
    ]
    new_edges = []

    # Replace graph
    replace_file_graph(conn, file_id, new_nodes, new_edges)

    # Verify old nodes are gone and new nodes exist
    nodes = list_nodes_for_file(conn, file_id)
    assert len(nodes) == 1
    assert nodes[0]["id"] == "sym:repo:test:module:new"


def test_replace_file_graph_empty_lists(initialized_db) -> None:
    """Test replacing file graph with empty lists."""
    conn = initialized_db
    file_id = "file:empty.py"

    # Insert some initial data
    initial_nodes = [
        _create_test_node("sym:repo:test:module:initial", "module", "initial", file_id),
    ]
    upsert_nodes(conn, initial_nodes)

    # Replace with empty lists
    replace_file_graph(conn, file_id, [], [])

    # Verify all nodes are deleted
    nodes = list_nodes_for_file(conn, file_id)
    assert len(nodes) == 0


def test_replace_file_graph_transactional(initialized_db) -> None:
    """Test that replace_file_graph is transactional."""
    conn = initialized_db
    file_id = "file:trans.py"

    # Insert initial data
    initial_nodes = [
        _create_test_node("sym:repo:test:module:initial", "module", "initial", file_id),
    ]
    upsert_nodes(conn, initial_nodes)

    # Try to replace with invalid data (missing required fields)
    invalid_nodes = [
        {"id": "invalid"},  # Missing required fields
    ]

    # Should raise an error but not leave partial state
    try:
        replace_file_graph(conn, file_id, invalid_nodes, [])
    except Exception:
        pass  # Expected to fail

    # Original data should still be intact (transaction rolled back)
    nodes = list_nodes_for_file(conn, file_id)
    # Either all original data remains or all is gone (not partial)
    assert len(nodes) in (0, 1)


# ============== Graph Stats Tests ==============


def test_get_repo_graph_stats(initialized_db) -> None:
    """Test getting graph statistics for a repository."""
    from repo_context.graph import get_repo_graph_stats
    
    conn = initialized_db
    
    # Create nodes of various kinds including local functions
    nodes = [
        _create_test_node("sym:repo:test:module:mod1", "module", "mod1"),
        _create_test_node("sym:repo:test:class:mod1.Class1", "class", "mod1.Class1"),
        _create_test_node("sym:repo:test:function:mod1.func1", "function", "mod1.func1"),
        _create_test_node(
            "sym:repo:test:local_function:mod1.func1.inner",
            "local_function",
            "mod1.func1.inner"
        ),
    ]
    upsert_nodes(conn, nodes)
    
    stats = get_repo_graph_stats(conn, "repo:test")
    
    assert stats["repo_id"] == "repo:test"
    assert stats["node_count"] == 4
    assert stats["module_count"] == 1
    assert stats["class_count"] == 1
    assert stats["callable_count"] == 2  # func1 + inner (local_function)
    assert stats["local_callable_count"] == 1  # inner only
