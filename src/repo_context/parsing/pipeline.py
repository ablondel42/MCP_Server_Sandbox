"""Per-file AST extraction pipeline with nested scope support."""

import ast
import json
from pathlib import Path
from typing import Any

from repo_context.models.file import FileRecord
from repo_context.parsing.ast_loader import load_file_text, parse_file
from repo_context.parsing.module_extractor import extract_module_node
from repo_context.parsing.class_extractor import extract_class_nodes
from repo_context.parsing.callable_extractor import extract_callable_nodes
from repo_context.parsing.import_extractor import extract_import_edges_and_payload
from repo_context.parsing.inheritance_extractor import extract_inheritance_edges
from repo_context.parsing.naming import build_module_qualified_name, DuplicateTracker
from repo_context.parsing.scope_tracker import ScopeTracker


def extract_file_graph(
    repo_id: str,
    file_record: FileRecord,
    repo_root: Path,
) -> tuple[list[dict], list[dict], dict]:
    """Extract all nodes and edges for a single Python file with nested scope support.

    Args:
        repo_id: Repository ID.
        file_record: File record from Phase 2.
        repo_root: Repository root path.

    Returns:
        Tuple of (nodes list, edges list, summary dict).

    Raises:
        FileNotFoundError: If file cannot be read.
        SyntaxError: If file contains syntax errors.
    """
    # Step 1: Load file text
    file_path = repo_root / file_record.file_path
    file_text = load_file_text(file_path)

    # Step 2: Parse AST
    tree = parse_file(file_text)

    # Initialize trackers for nested extraction
    scope_tracker = ScopeTracker()
    duplicate_tracker = DuplicateTracker()

    # Step 3: Create module node
    module_node = extract_module_node(repo_id, file_record, tree, file_text, scope_tracker, duplicate_tracker)
    module_node_id = module_node["id"]
    module_path = file_record.module_path

    nodes = [module_node]
    edges = []

    # Step 4: Extract import edges and payload data
    import_edges, imported_modules, imported_symbols = extract_import_edges_and_payload(
        repo_id, module_node_id, file_record, tree
    )
    edges.extend(import_edges)

    # Step 5: Extract top-level class nodes with scope tracking
    class_nodes, class_contains_edges = extract_class_nodes(
        repo_id, file_record, module_node_id, module_path, tree, scope_tracker, duplicate_tracker, file_text=file_text
    )
    nodes.extend(class_nodes)
    edges.extend(class_contains_edges)

    # Step 6: Create module -> class contains edges and SCOPE_PARENT edges
    for class_node in class_nodes:
        contains_edge = _make_contains_edge(
            repo_id, module_node_id, class_node["id"], file_record, tree
        )
        edges.append(contains_edge)
        
        # Add SCOPE_PARENT edge for nested classes
        if class_node.get("lexical_parent_id"):
            scope_parent_edge = _make_scope_parent_edge(
                repo_id, class_node["id"], class_node["lexical_parent_id"], file_record
            )
            edges.append(scope_parent_edge)

    # Step 7: Extract inherits edges for each class
    inheritance_edges = extract_inheritance_edges(repo_id, file_record, class_nodes, tree)
    edges.extend(inheritance_edges)

    # Step 8: Extract top-level callable nodes (functions, async functions) with scope tracking
    top_level_callables = _extract_top_level_callables(
        repo_id, file_record, module_node_id, module_path, tree, scope_tracker, duplicate_tracker, file_text
    )
    nodes.extend(top_level_callables)

    # Step 11: Create module -> callable contains edges and SCOPE_PARENT edges
    for callable_node in top_level_callables:
        contains_edge = _make_contains_edge(
            repo_id, module_node_id, callable_node["id"], file_record, tree
        )
        edges.append(contains_edge)
        
        # Add SCOPE_PARENT edge for nested callables
        if callable_node.get("lexical_parent_id"):
            scope_parent_edge = _make_scope_parent_edge(
                repo_id, callable_node["id"], callable_node["lexical_parent_id"], file_record
            )
            edges.append(scope_parent_edge)

    # Step 12: Update module payload
    module_payload = json.loads(module_node["payload_json"])
    module_payload["imported_modules"] = imported_modules
    module_payload["imported_symbols"] = imported_symbols
    module_payload["top_level_symbol_ids"] = (
        [c["id"] for c in class_nodes] + [c["id"] for c in top_level_callables]
    )
    module_node["payload_json"] = json.dumps(module_payload, sort_keys=True)

    # Build summary
    method_count = sum(1 for n in nodes if n["kind"] in ("method", "async_method"))
    local_callable_count = sum(1 for n in nodes if n["kind"] in ("local_function", "local_async_function"))
    callable_count = len(top_level_callables) + method_count + local_callable_count
    
    summary = {
        "file_id": file_record.id,
        "file_path": file_record.file_path,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "module_count": 1,
        "class_count": len(class_nodes),
        "callable_count": callable_count,
        "method_count": method_count,
    }

    return nodes, edges, summary


def _ast_ClassDef_check(node: Any, class_name: str) -> bool:
    """Check if node is a ClassDef with matching name."""
    return isinstance(node, ast.ClassDef) and node.name == class_name


def _extract_class_methods(
    repo_id: str,
    file_record: FileRecord,
    class_node_id: str,
    class_qualified_name: str,
    class_ast_node: ast.ClassDef,
    scope_tracker: ScopeTracker,
    duplicate_tracker: DuplicateTracker,
    module_path: str,
    file_text: str,
) -> list[dict]:
    """Extract method nodes from a class AST node.

    Args:
        repo_id: Repository ID.
        file_record: File record.
        class_node_id: Parent class node ID.
        class_qualified_name: Parent class qualified name.
        class_ast_node: AST ClassDef node.
        scope_tracker: Scope tracker for lexical nesting.
        duplicate_tracker: Duplicate tracker for symbol ID disambiguation.
        module_path: Module path for qualified name building.

    Returns:
        List of method node dicts.
    """
    methods = []
    for node in class_ast_node.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(node)

    return extract_callable_nodes(
        repo_id=repo_id,
        file_record=file_record,
        parent_id=class_node_id,
        parent_qualified_name=class_qualified_name,
        nodes=methods,
        scope_tracker=scope_tracker,
        duplicate_tracker=duplicate_tracker,
        module_path=module_path,
        file_text=file_text,
    )


def _extract_top_level_callables(
    repo_id: str,
    file_record: FileRecord,
    module_node_id: str,
    module_path: str,
    tree: ast.Module,
    scope_tracker: ScopeTracker,
    duplicate_tracker: DuplicateTracker,
    file_text: str,
) -> list[dict]:
    """Extract top-level function and async function nodes.

    Args:
        repo_id: Repository ID.
        file_record: File record.
        module_node_id: Parent module node ID.
        module_path: Module path.
        tree: AST module.
        scope_tracker: Scope tracker for lexical nesting.
        duplicate_tracker: Duplicate tracker for symbol ID disambiguation.

    Returns:
        List of callable node dicts.
    """
    callables = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            callables.append(node)

    return extract_callable_nodes(
        repo_id=repo_id,
        file_record=file_record,
        parent_id=module_node_id,
        parent_qualified_name=module_path,
        nodes=callables,
        scope_tracker=scope_tracker,
        duplicate_tracker=duplicate_tracker,
        module_path=module_path,
        file_text=file_text,
    )


def _make_contains_edge(
    repo_id: str,
    from_id: str,
    to_id: str,
    file_record: FileRecord,
    evidence_node: ast.AST,
) -> dict:
    """Create a contains edge.

    Args:
        repo_id: Repository ID.
        from_id: Parent node ID.
        to_id: Child node ID.
        file_record: File record.
        evidence_node: AST node for evidence range.

    Returns:
        Contains edge dict.
    """
    # Create range from evidence node
    if hasattr(evidence_node, "lineno") and evidence_node.lineno is not None:
        start_line = evidence_node.lineno - 1
        start_col = getattr(evidence_node, "col_offset", 0)
        end_line = (getattr(evidence_node, "end_lineno", None) or evidence_node.lineno) - 1
        end_col = getattr(evidence_node, "end_col_offset", start_col)
        evidence_range = {
            "start": {"line": start_line, "character": start_col},
            "end": {"line": end_line, "character": end_col}
        }
    else:
        evidence_range = None

    return {
        "id": f"edge:{repo_id}:contains:{from_id}->{to_id}",
        "repo_id": repo_id,
        "kind": "contains",
        "from_id": from_id,
        "to_id": to_id,
        "source": "python-ast",
        "confidence": 1.0,
        "evidence_file_id": file_record.id,
        "evidence_uri": file_record.uri,
        "evidence_range_json": json.dumps(evidence_range, sort_keys=True) if evidence_range else None,
        "payload_json": "{}",
        "last_indexed_at": file_record.last_indexed_at,
    }


def _make_scope_parent_edge(
    repo_id: str,
    from_id: str,
    to_id: str,
    file_record: FileRecord,
) -> dict:
    """Create a SCOPE_PARENT edge for lexical nesting.

    Args:
        repo_id: Repository ID.
        from_id: Nested declaration node ID.
        to_id: Immediate lexical parent node ID.
        file_record: File record.

    Returns:
        SCOPE_PARENT edge dict.
    """
    return {
        "id": f"edge:{repo_id}:scope_parent:{from_id}->{to_id}",
        "repo_id": repo_id,
        "kind": "SCOPE_PARENT",
        "from_id": from_id,
        "to_id": to_id,
        "source": "python-ast",
        "confidence": 1.0,
        "evidence_file_id": file_record.id,
        "evidence_uri": file_record.uri,
        "evidence_range_json": None,
        "payload_json": "{}",
        "last_indexed_at": file_record.last_indexed_at,
    }


def _method_belongs_to_class(method_id: str, class_qualified_name: str) -> bool:
    """Check if a method ID belongs to a class.

    Args:
        method_id: Method node ID.
        class_qualified_name: Class qualified name.

    Returns:
        True if method belongs to class.
    """
    return method_id.startswith(f"sym:") and class_qualified_name in method_id
