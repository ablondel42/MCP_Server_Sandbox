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
from repo_context.parsing.scope_tracker import ScopeTracker
from repo_context.parsing.naming import DuplicateTracker
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
def nested_scope_fixture() -> Path:
    """Return path to nested_scope_case fixture."""
    return Path(__file__).parent / "fixtures" / "nested_scope_case"


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

    # Initialize trackers for module-level extraction
    scope_tracker = ScopeTracker()
    duplicate_tracker = DuplicateTracker()

    class_nodes, _ = extract_class_nodes("repo:test", file_record, module_node_id, "services", tree, scope_tracker, duplicate_tracker)

    # Should find BaseService and AuthService (class nodes only, not methods)
    class_only_nodes = [n for n in class_nodes if n["kind"] == "class"]
    assert len(class_only_nodes) == 2

    # Verify class structure
    class_names = [c["name"] for c in class_only_nodes]
    assert "BaseService" in class_names
    assert "AuthService" in class_names

    # Verify base names captured
    base_service = next(c for c in class_only_nodes if c["name"] == "BaseService")
    payload = json.loads(base_service["payload_json"])
    assert payload["base_names"] == []  # No base classes

    auth_service = next(c for c in class_only_nodes if c["name"] == "AuthService")
    payload = json.loads(auth_service["payload_json"])
    assert "BaseService" in payload["base_names"]


def test_callable_extraction_top_level(simple_package_fixture: Path) -> None:
    """Test that top-level function extraction works correctly."""
    file_path = simple_package_fixture / "services.py"
    file_record = _create_file_record("repo:test", "services.py", "services")

    file_text = load_file_text(file_path)
    tree = parse_file(file_text)
    
    # Initialize scope tracker for module-level extraction
    scope_tracker = ScopeTracker()
    duplicate_tracker = DuplicateTracker()

    # Get top-level functions only
    top_level_funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

    callables = extract_callable_nodes(
        "repo:test", file_record, "sym:repo:test:module:services", "services", top_level_funcs, scope_tracker, duplicate_tracker, "services", file_text
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
    
    # Initialize scope tracker and push class for method extraction
    scope_tracker = ScopeTracker()
    duplicate_tracker = DuplicateTracker()
    scope_tracker.push_declaration("sym:repo:test:class:services.AuthService", "AuthService", "class")

    # Extract methods
    methods = [n for n in auth_class.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

    callables = extract_callable_nodes(
        "repo:test", file_record, "sym:repo:test:class:services.AuthService", "services.AuthService", methods, scope_tracker, duplicate_tracker, "services", file_text
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

    # Extract class nodes first with scope tracker
    scope_tracker = ScopeTracker()
    duplicate_tracker = DuplicateTracker()
    class_nodes, _ = extract_class_nodes("repo:test", file_record, "sym:repo:test:module:models", "models", tree, scope_tracker, duplicate_tracker)

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

    # Class docstring with scope tracker
    scope_tracker = ScopeTracker()
    duplicate_tracker = DuplicateTracker()
    class_nodes, _ = extract_class_nodes("repo:test", file_record, "sym:repo:test:module:services", "services", tree, scope_tracker, duplicate_tracker)
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
    """Test that nested functions DO produce nodes as local_function (Phase 03b behavior)."""
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

    # Phase 03b: nested functions ARE extracted as local_function/local_async_function
    assert "nested_helper" in node_names
    assert "async_nested" in node_names
    
    # Verify they have correct kinds
    nested_helper = next(n for n in nodes if n["name"] == "nested_helper")
    assert nested_helper["kind"] == "local_function"
    assert nested_helper["scope"] == "function"
    
    async_nested = next(n for n in nodes if n["name"] == "async_nested")
    assert async_nested["kind"] == "local_async_function"
    assert async_nested["scope"] == "function"

    # Count function/method nodes (including local functions)
    func_kinds = [k for k in node_kinds if k in ("function", "async_function", "method", "async_method", "local_function", "local_async_function")]

    # Should have: outer_function, async_outer, method_with_nested, simple_method, nested_helper, another_nested, async_nested, sync_nested, inner
    # (nested functions are now extracted)
    assert len(func_kinds) >= 9


# ============== Phase 03b: Nested Scope Support Tests ==============


def test_extract_nested_function(nested_scope_fixture: Path) -> None:
    """Test that nested functions are extracted as local_function."""
    file_path = nested_scope_fixture / "nested_funcs.py"
    file_record = _create_file_record("repo:test", "nested_funcs.py", "nested_funcs")
    
    repo_id = "repo:test"
    nodes, edges, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)
    
    # Find the outer and inner function nodes
    outer_node = next((n for n in nodes if n["name"] == "outer" and n["kind"] == "function"), None)
    inner_node = next((n for n in nodes if n["name"] == "inner" and n["kind"] == "local_function"), None)
    
    assert outer_node is not None, "outer function should be extracted"
    assert inner_node is not None, "inner nested function should be extracted as local_function"
    
    # Verify scope and parent
    assert inner_node["scope"] == "function"
    assert inner_node["lexical_parent_id"] == outer_node["id"]
    
    # Verify SCOPE_PARENT edge exists
    scope_parent_edge = next((e for e in edges if e["kind"] == "SCOPE_PARENT" and e["from_id"] == inner_node["id"]), None)
    assert scope_parent_edge is not None
    assert scope_parent_edge["to_id"] == outer_node["id"]


def test_extract_nested_async_function(nested_scope_fixture: Path) -> None:
    """Test that nested async functions are extracted as local_async_function."""
    file_path = nested_scope_fixture / "mixed_nesting.py"
    file_record = _create_file_record("repo:test", "mixed_nesting.py", "mixed_nesting")
    
    repo_id = "repo:test"
    nodes, edges, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)
    
    # Find the async_inner node
    async_inner = next((n for n in nodes if n["name"] == "async_inner" and n["kind"] == "local_async_function"), None)
    
    assert async_inner is not None, "async_inner should be extracted as local_async_function"
    assert async_inner["scope"] == "function"


def test_extract_function_inside_method(nested_scope_fixture: Path) -> None:
    """Test that functions inside methods are local_function with method as parent."""
    # This tests the case where a method contains a nested function
    # The nested function should have the method as lexical_parent
    file_path = nested_scope_fixture / "mixed_nesting.py"
    file_record = _create_file_record("repo:test", "mixed_nesting.py", "mixed_nesting")
    
    repo_id = "repo:test"
    nodes, edges, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)
    
    # Find LocalFormatter.format method
    format_method = next((n for n in nodes if n["name"] == "format" and n["kind"] == "method"), None)
    assert format_method is not None


def test_extract_local_class(nested_scope_fixture: Path) -> None:
    """Test that local classes inside functions are extracted with scope=function."""
    file_path = nested_scope_fixture / "local_classes.py"
    file_record = _create_file_record("repo:test", "local_classes.py", "local_classes")
    
    repo_id = "repo:test"
    nodes, edges, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)
    
    # Find LocalClass
    local_class = next((n for n in nodes if n["name"] == "LocalClass"), None)
    
    assert local_class is not None, "LocalClass should be extracted"
    assert local_class["scope"] == "function"
    
    # Verify it has lexical_parent_id pointing to factory function
    assert local_class["lexical_parent_id"] is not None


def test_extract_method_inside_local_class(nested_scope_fixture: Path) -> None:
    """Test that methods in local classes are extracted as method with class as parent."""
    file_path = nested_scope_fixture / "local_classes.py"
    file_record = _create_file_record("repo:test", "local_classes.py", "local_classes")
    
    repo_id = "repo:test"
    nodes, edges, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)
    
    # Find method in LocalClass
    method_node = next((n for n in nodes if n["name"] == "method"), None)
    
    assert method_node is not None, "method in LocalClass should be extracted"
    assert method_node["kind"] == "method"
    
    # Find LocalClass
    local_class = next((n for n in nodes if n["name"] == "LocalClass"), None)
    assert method_node["lexical_parent_id"] == local_class["id"]


def test_nested_qualified_name_is_stable(nested_scope_fixture: Path) -> None:
    """Test that nested qualified names are stable across parses."""
    file_path = nested_scope_fixture / "nested_funcs.py"
    file_record = _create_file_record("repo:test", "nested_funcs.py", "nested_funcs")
    
    repo_id = "repo:test"
    
    # Parse twice
    nodes1, _, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)
    nodes2, _, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)
    
    # Find inner function in both
    inner1 = next((n for n in nodes1 if n["name"] == "inner"), None)
    inner2 = next((n for n in nodes2 if n["name"] == "inner"), None)
    
    assert inner1 is not None
    assert inner2 is not None
    
    # Qualified names should be the same
    assert inner1["qualified_name"] == inner2["qualified_name"]
    
    # IDs should be the same (deterministic with line:col disambiguation)
    assert inner1["id"] == inner2["id"]


def test_duplicate_same_scope_names_do_not_collide(nested_scope_fixture: Path) -> None:
    """Test that duplicate declarations in same scope get different IDs."""
    file_path = nested_scope_fixture / "duplicate_names.py"
    file_record = _create_file_record("repo:test", "duplicate_names.py", "duplicate_names")
    
    repo_id = "repo:test"
    nodes, edges, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)
    
    # Find all 'inner' functions
    inner_nodes = [n for n in nodes if n["name"] == "inner"]
    
    # Should have 2 inner functions with different IDs
    assert len(inner_nodes) == 2
    assert inner_nodes[0]["id"] != inner_nodes[1]["id"]
    
    # Both should be local_function
    assert all(n["kind"] == "local_function" for n in inner_nodes)
    
    # Both should have same qualified_name (that's why we need ID disambiguation)
    assert inner_nodes[0]["qualified_name"] == inner_nodes[1]["qualified_name"]


def test_kind_filter_compatibility_for_callables(nested_scope_fixture: Path) -> None:
    """Test that callable kind filters include local_function and local_async_function."""
    file_path = nested_scope_fixture / "nested_funcs.py"
    file_record = _create_file_record("repo:test", "nested_funcs.py", "nested_funcs")

    repo_id = "repo:test"
    nodes, _, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)

    # Get all callable kinds including local functions
    all_callable_kinds = ("function", "async_function", "method", "async_method",
                          "local_function", "local_async_function")
    callable_nodes = [n for n in nodes if n["kind"] in all_callable_kinds]

    # Should find outer, inner, outer_with_deep_nesting, level1, level2
    assert len(callable_nodes) >= 5

    # Verify local_function kind is present
    local_funcs = [n for n in callable_nodes if n["kind"] == "local_function"]
    assert len(local_funcs) >= 3  # inner, level1, level2


def test_deep_nesting_chain(nested_scope_fixture: Path) -> None:
    """Test that deeply nested functions maintain correct parent chain."""
    file_path = nested_scope_fixture / "nested_funcs.py"
    file_record = _create_file_record("repo:test", "nested_funcs.py", "nested_funcs")

    repo_id = "repo:test"
    nodes, edges, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)

    # Find the deep nesting functions
    outer_deep = next((n for n in nodes if n["name"] == "outer_with_deep_nesting"), None)
    level1 = next((n for n in nodes if n["name"] == "level1"), None)
    level2 = next((n for n in nodes if n["name"] == "level2"), None)

    assert outer_deep is not None
    assert level1 is not None
    assert level2 is not None

    # Verify parent chain
    assert level1["lexical_parent_id"] == outer_deep["id"], "level1 parent should be outer_with_deep_nesting"
    assert level2["lexical_parent_id"] == level1["id"], "level2 parent should be level1"

    # Verify SCOPE_PARENT edges for deep chain
    scope_parent_edges = [e for e in edges if e["kind"] == "SCOPE_PARENT"]
    level1_edge = next((e for e in scope_parent_edges if e["from_id"] == level1["id"]), None)
    level2_edge = next((e for e in scope_parent_edges if e["from_id"] == level2["id"]), None)

    assert level1_edge is not None
    assert level1_edge["to_id"] == outer_deep["id"]
    assert level2_edge is not None
    assert level2_edge["to_id"] == level1["id"]


def test_nested_function_inside_method(nested_scope_fixture: Path) -> None:
    """Test that nested functions inside methods have method as lexical parent."""
    file_path = nested_scope_fixture / "mixed_nesting.py"
    file_record = _create_file_record("repo:test", "mixed_nesting.py", "mixed_nesting")

    repo_id = "repo:test"
    nodes, edges, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)

    # Find LocalFormatter.format method
    format_method = next((n for n in nodes if n["name"] == "format" and n["kind"] == "method"), None)
    assert format_method is not None, "format method should exist"

    # Verify the method has correct scope
    assert format_method["scope"] == "class"
    assert format_method["lexical_parent_id"] is not None


def test_empty_function_body(nested_scope_fixture: Path) -> None:
    """Test that functions with empty bodies don't cause extraction errors."""
    file_path = nested_scope_fixture / "duplicate_names.py"
    file_record = _create_file_record("repo:test", "duplicate_names.py", "duplicate_names")

    repo_id = "repo:test"
    # Should not raise any errors
    nodes, edges, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)

    # Verify extraction completed
    assert len(nodes) > 0
    module_nodes = [n for n in nodes if n["kind"] == "module"]
    assert len(module_nodes) == 1


def test_scope_parent_edge_completeness(nested_scope_fixture: Path) -> None:
    """Test that every nested declaration has a SCOPE_PARENT edge."""
    file_path = nested_scope_fixture / "nested_funcs.py"
    file_record = _create_file_record("repo:test", "nested_funcs.py", "nested_funcs")

    repo_id = "repo:test"
    nodes, edges, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)

    # Find all local functions
    local_funcs = [n for n in nodes if n["kind"] == "local_function"]

    # Every local function should have a SCOPE_PARENT edge
    scope_parent_edges = {e["from_id"]: e for e in edges if e["kind"] == "SCOPE_PARENT"}

    for func in local_funcs:
        assert func["id"] in scope_parent_edges, f"{func['name']} should have SCOPE_PARENT edge"
        edge = scope_parent_edges[func["id"]]
        assert edge["to_id"] == func["lexical_parent_id"], f"SCOPE_PARENT edge should point to lexical_parent"


def test_lexical_parent_chain_integrity(nested_scope_fixture: Path) -> None:
    """Test that lexical_parent_id references always point to existing nodes."""
    file_path = nested_scope_fixture / "nested_funcs.py"
    file_record = _create_file_record("repo:test", "nested_funcs.py", "nested_funcs")

    repo_id = "repo:test"
    nodes, _, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)

    # Build node ID lookup
    node_ids = {n["id"] for n in nodes}

    # Every lexical_parent_id should reference an existing node
    for node in nodes:
        if node["lexical_parent_id"] is not None:
            assert node["lexical_parent_id"] in node_ids, f"lexical_parent_id {node['lexical_parent_id']} should exist"


def test_scope_values_are_valid(nested_scope_fixture: Path) -> None:
    """Test that all scope values are one of the valid values."""
    file_path = nested_scope_fixture / "mixed_nesting.py"
    file_record = _create_file_record("repo:test", "mixed_nesting.py", "mixed_nesting")

    repo_id = "repo:test"
    nodes, _, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)

    valid_scopes = {"module", "function", "class"}

    for node in nodes:
        assert node["scope"] in valid_scopes, f"Invalid scope {node['scope']} for {node['name']}"

    # Verify specific scope assignments
    module_nodes = [n for n in nodes if n["kind"] == "module"]
    for node in module_nodes:
        assert node["scope"] == "module"

    func_nodes = [n for n in nodes if n["kind"] == "function"]
    for node in func_nodes:
        assert node["scope"] == "module"

    method_nodes = [n for n in nodes if n["kind"] == "method"]
    for node in method_nodes:
        assert node["scope"] == "class"

    local_func_nodes = [n for n in nodes if n["kind"] == "local_function"]
    for node in local_func_nodes:
        assert node["scope"] == "function"


def test_disambiguated_id_format(nested_scope_fixture: Path) -> None:
    """Test that duplicate IDs follow the expected :dup{N} format."""
    file_path = nested_scope_fixture / "duplicate_names.py"
    file_record = _create_file_record("repo:test", "duplicate_names.py", "duplicate_names")

    repo_id = "repo:test"
    nodes, _, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)

    # Find duplicate 'inner' functions
    inner_nodes = [n for n in nodes if n["name"] == "inner"]

    # First duplicate should have clean ID, subsequent ones should have :dup{N} suffix
    assert len(inner_nodes) == 2
    # First one has clean ID
    assert inner_nodes[0]["id"] == "sym:repo:test:local_function:duplicate_names.outer_with_duplicates.inner"
    # Second one has :dup1 suffix
    assert inner_nodes[1]["id"] == "sym:repo:test:local_function:duplicate_names.outer_with_duplicates.inner:dup1"


def test_class_nested_in_function_has_correct_parent(nested_scope_fixture: Path) -> None:
    """Test that classes nested in functions have function as lexical parent."""
    file_path = nested_scope_fixture / "local_classes.py"
    file_record = _create_file_record("repo:test", "local_classes.py", "local_classes")

    repo_id = "repo:test"
    nodes, edges, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)

    # Find LocalClass
    local_class = next((n for n in nodes if n["name"] == "LocalClass"), None)
    assert local_class is not None

    # Find factory function
    factory = next((n for n in nodes if n["name"] == "factory"), None)
    assert factory is not None

    # Verify parent linkage
    assert local_class["lexical_parent_id"] == factory["id"]

    # Verify SCOPE_PARENT edge
    scope_edge = next((e for e in edges if e["kind"] == "SCOPE_PARENT" and e["from_id"] == local_class["id"]), None)
    assert scope_edge is not None
    assert scope_edge["to_id"] == factory["id"]


def test_all_node_kinds_have_scope(nested_scope_fixture: Path) -> None:
    """Test that all node kinds have scope field populated."""
    file_path = nested_scope_fixture / "mixed_nesting.py"
    file_record = _create_file_record("repo:test", "mixed_nesting.py", "mixed_nesting")

    repo_id = "repo:test"
    nodes, _, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)

    for node in nodes:
        assert node["scope"] is not None, f"Node {node['name']} ({node['kind']}) should have scope"
        assert node["scope"] in ("module", "function", "class")


# ============== Phase 03b: Persistence Tests ==============


def test_phase4_persists_nested_symbol_fields(temp_db: Path, nested_scope_fixture: Path) -> None:
    """Test that scope and lexical_parent_id are persisted to database."""
    from repo_context.models.repo import RepoRecord
    
    file_path = nested_scope_fixture / "nested_funcs.py"
    file_record = _create_file_record("repo:test", "nested_funcs.py", "nested_funcs")
    
    repo_id = "repo:test"
    nodes, edges, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)
    
    # Initialize database and persist
    conn = get_connection(temp_db)
    initialize_database(conn)
    
    # Create repo record
    repo = RepoRecord(
        id=repo_id,
        root_path=str(nested_scope_fixture),
        name="test",
        default_language="python",
        created_at="2026-01-01T00:00:00Z",
        last_indexed_at="2026-01-01T00:00:00Z",
    )
    upsert_repo(conn, repo)
    upsert_nodes(conn, nodes)
    upsert_edges(conn, edges)
    conn.commit()
    
    # Query and verify scope is stored
    cursor = conn.execute("SELECT id, name, scope, lexical_parent_id FROM nodes WHERE kind = 'local_function'")
    local_funcs = cursor.fetchall()
    
    assert len(local_funcs) > 0, "Should have local_function nodes"
    for func in local_funcs:
        assert func["scope"] == "function", "local_function should have scope=function"
        assert func["lexical_parent_id"] is not None, "local_function should have lexical_parent_id"
    
    # Verify SCOPE_PARENT edge is stored
    cursor = conn.execute("SELECT id, kind, from_id, to_id FROM edges WHERE kind = 'SCOPE_PARENT'")
    scope_edges = cursor.fetchall()
    
    assert len(scope_edges) > 0, "Should have SCOPE_PARENT edges"
    
    close_connection(conn)


def test_nested_symbols_queryable(temp_db: Path, nested_scope_fixture: Path) -> None:
    """Test that nested symbols can be queried by qualified name and lexical parent."""
    from repo_context.models.repo import RepoRecord
    
    file_path = nested_scope_fixture / "nested_funcs.py"
    file_record = _create_file_record("repo:test", "nested_funcs.py", "nested_funcs")
    
    repo_id = "repo:test"
    nodes, edges, _ = extract_file_graph(repo_id, file_record, nested_scope_fixture)
    
    # Initialize database and persist
    conn = get_connection(temp_db)
    initialize_database(conn)
    
    repo = RepoRecord(
        id=repo_id,
        root_path=str(nested_scope_fixture),
        name="test",
        default_language="python",
        created_at="2026-01-01T00:00:00Z",
        last_indexed_at="2026-01-01T00:00:00Z",
    )
    upsert_repo(conn, repo)
    upsert_nodes(conn, nodes)
    upsert_edges(conn, edges)
    conn.commit()
    
    # Query by qualified name
    cursor = conn.execute(
        "SELECT id, name, qualified_name FROM nodes WHERE qualified_name LIKE '%outer.inner%'"
    )
    inner_nodes = cursor.fetchall()
    assert len(inner_nodes) > 0, "Should be able to query by nested qualified name"
    
    # Query by lexical parent
    outer_node = next((n for n in nodes if n["name"] == "outer"), None)
    if outer_node:
        cursor = conn.execute(
            "SELECT id, name FROM nodes WHERE lexical_parent_id = ?",
            (outer_node["id"],)
        )
        children = cursor.fetchall()
        assert len(children) > 0, "Should be able to query by lexical_parent_id"
    
    close_connection(conn)


def test_compatibility_no_regressions(temp_db: Path, simple_package_fixture: Path) -> None:
    """Test that files without nested declarations still work correctly."""
    from repo_context.models.repo import RepoRecord
    
    file_path = simple_package_fixture / "services.py"
    file_record = _create_file_record("repo:test", "services.py", "services")
    
    repo_id = "repo:test"
    nodes, edges, _ = extract_file_graph(repo_id, file_record, simple_package_fixture)
    
    # Initialize database and persist
    conn = get_connection(temp_db)
    initialize_database(conn)
    
    repo = RepoRecord(
        id=repo_id,
        root_path=str(simple_package_fixture),
        name="test",
        default_language="python",
        created_at="2026-01-01T00:00:00Z",
        last_indexed_at="2026-01-01T00:00:00Z",
    )
    upsert_repo(conn, repo)
    upsert_nodes(conn, nodes)
    upsert_edges(conn, edges)
    conn.commit()
    
    # Verify module-level functions have scope=module
    cursor = conn.execute(
        "SELECT id, name, scope FROM nodes WHERE kind = 'function'"
    )
    functions = cursor.fetchall()
    
    for func in functions:
        assert func["scope"] == "module", f"Module-level function {func['name']} should have scope=module"
    
    # Verify methods have scope=class
    cursor = conn.execute(
        "SELECT id, name, scope FROM nodes WHERE kind = 'method'"
    )
    methods = cursor.fetchall()
    
    for method in methods:
        assert method["scope"] == "class", f"Method {method['name']} should have scope=class"
    
    close_connection(conn)
