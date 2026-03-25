"""AST extraction tests."""

import ast
import json
import tempfile
from pathlib import Path

import pytest

from repo_context.models.file import FileRecord
from repo_context.parsing.ast_loader import load_file_text, parse_file
from repo_context.parsing.module_extractor import extract_module_node
from repo_context.parsing.class_extractor import extract_class_nodes
from repo_context.parsing.callable_extractor import extract_callable_nodes
from repo_context.parsing.import_extractor import extract_import_edges_and_payload
from repo_context.parsing.inheritance_extractor import extract_inheritance_edges
from repo_context.parsing.pipeline import extract_file_graph
from repo_context.parsing.ranges import make_range, make_name_selection_range, to_zero_based_line
from repo_context.parsing.docstrings import get_doc_summary
from repo_context.storage import (
    get_connection,
    close_connection,
    initialize_database,
    upsert_repo,
    upsert_files,
    upsert_nodes,
    upsert_edges,
    list_nodes_for_file,
    list_edges_for_repo,
)


@pytest.fixture
def temp_db() -> Path:
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


@pytest.fixture
def simple_package_fixture() -> Path:
    """Return path to simple_package fixture."""
    return Path(__file__).parent / "fixtures" / "simple_package"


@pytest.fixture
def nested_functions_fixture() -> Path:
    """Return path to nested_functions_case fixture."""
    return Path(__file__).parent / "fixtures" / "nested_functions_case"


@pytest.fixture
def inheritance_fixture() -> Path:
    """Return path to inheritance_case fixture."""
    return Path(__file__).parent / "fixtures" / "inheritance_case"


def _create_file_record(repo_id: str, file_path: str, module_path: str) -> FileRecord:
    """Create a test file record."""
    return FileRecord(
        id=f"file:{file_path}",
        repo_id=repo_id,
        file_path=file_path,
        uri=f"file:///test/{file_path}",
        module_path=module_path,
        language="python",
        content_hash="sha256:test",
        size_bytes=100,
        last_modified_at="2026-01-01T00:00:00Z",
        last_indexed_at="2026-01-01T00:00:00Z",
    )


def test_module_extraction(simple_package_fixture: Path) -> None:
    """Test that module extraction produces correct nodes."""
    file_path = simple_package_fixture / "services.py"
    file_record = _create_file_record("repo:test", "services.py", "services")
    
    file_text = load_file_text(file_path)
    tree = parse_file(file_text)
    module_node = extract_module_node("repo:test", file_record, tree, file_text)
    
    # Verify module node structure
    assert module_node["kind"] == "module"
    assert module_node["qualified_name"] == "services"
    assert module_node["parent_id"] is None
    assert module_node["source"] == "python-ast"
    assert module_node["confidence"] == 1.0
    
    # Verify payload
    payload = json.loads(module_node["payload_json"])
    assert payload["module_path"] == "services"
    assert payload["file_path"] == "services.py"


def test_class_extraction(simple_package_fixture: Path) -> None:
    """Test that class extraction produces correct nodes."""
    file_path = simple_package_fixture / "services.py"
    file_record = _create_file_record("repo:test", "services.py", "services")
    
    file_text = load_file_text(file_path)
    tree = parse_file(file_text)
    module_node_id = "sym:repo:test:module:services"
    
    class_nodes = extract_class_nodes("repo:test", file_record, module_node_id, "services", tree)
    
    # Should find BaseService and AuthService
    assert len(class_nodes) == 2
    
    # Verify class structure
    class_names = [c["name"] for c in class_nodes]
    assert "BaseService" in class_names
    assert "AuthService" in class_names
    
    # Verify base names captured
    base_service = next(c for c in class_nodes if c["name"] == "BaseService")
    payload = json.loads(base_service["payload_json"])
    assert payload["base_names"] == []  # No base classes
    
    auth_service = next(c for c in class_nodes if c["name"] == "AuthService")
    payload = json.loads(auth_service["payload_json"])
    assert "BaseService" in payload["base_names"]


def test_callable_extraction_top_level(simple_package_fixture: Path) -> None:
    """Test that top-level function extraction works correctly."""
    file_path = simple_package_fixture / "services.py"
    file_record = _create_file_record("repo:test", "services.py", "services")
    
    file_text = load_file_text(file_path)
    tree = parse_file(file_text)
    
    # Get top-level functions only
    top_level_funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    
    callables = extract_callable_nodes(
        "repo:test", file_record, "sym:repo:test:module:services", "services", top_level_funcs, is_method=False
    )
    
    # Should find create_service (function) and fetch_data (async_function)
    assert len(callables) == 2
    
    kinds = [c["kind"] for c in callables]
    assert "function" in kinds
    assert "async_function" in kinds


def test_callable_extraction_methods(simple_package_fixture: Path) -> None:
    """Test that method extraction works correctly."""
    file_path = simple_package_fixture / "services.py"
    file_record = _create_file_record("repo:test", "services.py", "services")
    
    file_text = load_file_text(file_path)
    tree = parse_file(file_text)
    
    # Find AuthService class
    auth_class = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "AuthService":
            auth_class = node
            break
    
    assert auth_class is not None
    
    # Extract methods
    methods = [n for n in auth_class.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    
    callables = extract_callable_nodes(
        "repo:test", file_record, "sym:repo:test:class:services.AuthService", "services.AuthService", methods, is_method=True
    )
    
    # Should find login and logout methods
    assert len(callables) == 2
    
    kinds = [c["kind"] for c in callables]
    assert all(k == "method" for k in kinds)


def test_contains_edges(simple_package_fixture: Path) -> None:
    """Test that contains edges are created correctly."""
    file_path = simple_package_fixture / "services.py"
    repo_id = "repo:test"
    file_record = _create_file_record(repo_id, "services.py", "services")
    
    nodes, edges, _ = extract_file_graph(repo_id, file_record, simple_package_fixture)
    
    # Find contains edges
    contains_edges = [e for e in edges if e["kind"] == "contains"]
    
    # Should have module->class and module->function edges
    assert len(contains_edges) > 0
    
    # Verify edge structure
    for edge in contains_edges:
        assert edge["source"] == "python-ast"
        assert edge["confidence"] == 1.0
        assert edge["repo_id"] == repo_id


def test_import_edges(simple_package_fixture: Path) -> None:
    """Test that import edges are created correctly."""
    file_path = simple_package_fixture / "services.py"
    file_record = _create_file_record("repo:test", "services.py", "services")
    
    file_text = load_file_text(file_path)
    tree = parse_file(file_text)
    module_node_id = "sym:repo:test:module:services"
    
    edges, imported_modules, imported_symbols = extract_import_edges_and_payload(
        "repo:test", module_node_id, file_record, tree
    )
    
    # Should find typing import
    assert "typing" in imported_modules
    assert "Optional" in imported_symbols
    
    # Verify edge structure
    for edge in edges:
        assert edge["kind"] == "imports"
        assert edge["source"] == "python-ast"
        assert edge["confidence"] == 0.8
        assert edge["to_id"].startswith("external_or_unresolved:")


def test_inherits_edges(inheritance_fixture: Path) -> None:
    """Test that inheritance edges are created correctly."""
    file_path = inheritance_fixture / "models.py"
    file_record = _create_file_record("repo:test", "models.py", "models")
    
    file_text = load_file_text(file_path)
    tree = parse_file(file_text)
    
    # Extract class nodes first
    class_nodes = extract_class_nodes("repo:test", file_record, "sym:repo:test:module:models", "models", tree)
    
    # Extract inheritance edges
    edges = extract_inheritance_edges("repo:test", file_record, class_nodes, tree)
    
    # Should find inheritance for Mammal, Bird, Dog, Cat, Parrot, MultiInherit
    assert len(edges) >= 5
    
    # Verify edge structure
    for edge in edges:
        assert edge["kind"] == "inherits"
        assert edge["to_id"].startswith("unresolved_base:")
        assert edge["confidence"] == 0.75


def test_doc_summary_extraction(simple_package_fixture: Path) -> None:
    """Test that docstring summaries are extracted correctly."""
    file_path = simple_package_fixture / "services.py"
    file_record = _create_file_record("repo:test", "services.py", "services")
    
    file_text = load_file_text(file_path)
    tree = parse_file(file_text)
    
    # Module docstring
    module_summary = get_doc_summary(tree)
    assert module_summary is not None
    assert "Simple package" in module_summary
    
    # Class docstring
    class_nodes = extract_class_nodes("repo:test", file_record, "sym:repo:test:module:services", "services", tree)
    base_service = next(c for c in class_nodes if c["name"] == "BaseService")
    assert base_service["doc_summary"] is not None
    assert "Base service" in base_service["doc_summary"]


def test_range_extraction(simple_package_fixture: Path) -> None:
    """Test that range extraction produces zero-based line numbers."""
    file_path = simple_package_fixture / "services.py"
    file_record = _create_file_record("repo:test", "services.py", "services")
    
    file_text = load_file_text(file_path)
    tree = parse_file(file_text)
    
    # Find a class node
    class_node = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_node = node
            break
    
    assert class_node is not None
    
    # Test range extraction
    range_data = make_range(class_node)
    assert range_data is not None
    assert range_data["start"]["line"] >= 0  # Zero-based
    
    # Test selection range
    selection_range = make_name_selection_range(class_node)
    assert selection_range is not None
    assert selection_range["start"]["line"] >= 0  # Zero-based
    
    # Test line conversion
    assert to_zero_based_line(1) == 0
    assert to_zero_based_line(10) == 9
    assert to_zero_based_line(None) is None


def test_nested_functions_are_ignored(nested_functions_fixture: Path) -> None:
    """Test that nested functions do NOT produce nodes or edges."""
    file_path = nested_functions_fixture / "nested.py"
    file_record = _create_file_record("repo:test", "nested.py", "nested")
    
    repo_id = "repo:test"
    nodes, edges, _ = extract_file_graph(repo_id, file_record, nested_functions_fixture)
    
    # Get all node names
    node_names = [n["name"] for n in nodes]
    node_kinds = [n["kind"] for n in nodes]
    
    # Should have module, classes, and top-level callables
    assert "module" in node_kinds
    assert "OuterClass" in node_names
    
    # Should NOT have nested function names
    assert "nested_helper" not in node_names
    assert "another_nested" not in node_names
    assert "async_nested" not in node_names
    assert "sync_nested" not in node_names
    assert "inner" not in node_names
    
    # Count function/method nodes
    func_kinds = [k for k in node_kinds if k in ("function", "async_function", "method", "async_method")]
    
    # Should only have: outer_function, async_outer, method_with_nested, simple_method
    # NOT the nested ones
    assert len(func_kinds) == 4
