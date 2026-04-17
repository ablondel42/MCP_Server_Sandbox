"""Class node extraction from Python AST."""

import ast
import json
from typing import Optional

from repo_context.models.file import FileRecord
from repo_context.parsing.naming import (
    build_class_qualified_name,
    build_nested_qualified_name,
    DuplicateTracker,
)
from repo_context.parsing.ranges import make_range, make_name_selection_range
from repo_context.parsing.docstrings import get_doc_summary
from repo_context.parsing.scope_tracker import ScopeTracker
import repo_context.parsing.callable_extractor
import hashlib


def extract_class_nodes(
    repo_id: str,
    file_record: FileRecord,
    module_node_id: str,
    module_path: str,
    tree: ast.Module,
    scope_tracker: ScopeTracker,
    duplicate_tracker: DuplicateTracker,
    parent_id: Optional[str] = None,
    parent_qualified_name: Optional[str] = None,
    file_text: str = "",
) -> tuple[list[dict], list[dict]]:
    """Extract class nodes from class definitions.

    Args:
        repo_id: Repository ID.
        file_record: File record from Phase 2.
        module_node_id: Parent module node ID (for module-level classes).
        module_path: Module path for qualified name building.
        tree: Parsed AST module.
        scope_tracker: Scope tracker for lexical nesting.
        duplicate_tracker: Duplicate tracker for symbol ID disambiguation.
        parent_id: Optional parent ID (for nested classes).
        parent_qualified_name: Optional parent qualified name (for classes nested in functions).

    Returns:
        Tuple of (class nodes list, contains edges list).
    """
    nodes = []
    contains_edges = []

    # Only process top-level classes in tree.body
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue

        class_name = node.name

        # Determine scope based on current tracker state
        current_scope = scope_tracker.get_current_scope()
        lexical_parent_id = scope_tracker.get_lexical_parent_id()

        # Build qualified name
        if parent_qualified_name is not None:
            # Class is nested inside a function - use parent's qualified name
            qualified_name = f"{parent_qualified_name}.{class_name}"
        elif scope_tracker.is_empty():
            # Module-level class
            qualified_name = build_class_qualified_name(module_path, class_name)
        else:
            # Class nested in another scope
            lexical_chain = scope_tracker.get_lexical_chain()
            qualified_name = build_nested_qualified_name(module_path, lexical_chain, class_name)

        # Build symbol ID using duplicate tracker
        node_id = duplicate_tracker.get_symbol_id(repo_id, "class", qualified_name)

        # Extract base class names using ast.unparse
        base_names = []
        for base in node.bases:
            try:
                base_names.append(ast.unparse(base))
            except Exception:
                base_names.append("<unparsable>")

        # Extract decorators using ast.unparse
        decorators = []
        for decorator in node.decorator_list:
            try:
                decorators.append(ast.unparse(decorator))
            except Exception:
                decorators.append("<unparsable>")

        # Determine visibility
        if class_name.startswith("_"):
            visibility_hint = "private_like"
        else:
            visibility_hint = "public"

        class_node_dict = {
            "id": node_id,
            "repo_id": repo_id,
            "file_id": file_record.id,
            "language": "python",
            "kind": "class",
            "name": class_name,
            "qualified_name": qualified_name,
            "uri": file_record.uri,
            "range_json": make_range(node) if make_range(node) else None,
            "selection_range_json": make_name_selection_range(node) if make_name_selection_range(node) else None,
            "parent_id": lexical_parent_id,
            "visibility_hint": visibility_hint,
            "doc_summary": get_doc_summary(node),
            "content_hash": "",
            "semantic_hash": _compute_class_semantic_hash(qualified_name, base_names, decorators),
            "source": "python-ast",
            "confidence": 1.0,
            "scope": current_scope,
            "lexical_parent_id": lexical_parent_id,
            "payload_json": json.dumps({
                "base_names": base_names,
                "decorators": decorators,
                "method_ids": []
            }, sort_keys=True),
            "last_indexed_at": file_record.last_indexed_at,
        }

        nodes.append(class_node_dict)

        # Extract methods from class body and add to nodes
        method_nodes, method_contains_edges = _extract_methods_from_class(
            repo_id, file_record, node_id, qualified_name, node, scope_tracker, duplicate_tracker, module_path, file_text
        )
        nodes.extend(method_nodes)
        contains_edges.extend(method_contains_edges)

        # Update class payload with method IDs
        method_ids = [m["id"] for m in method_nodes]
        class_node_dict["payload_json"] = json.dumps({
            "base_names": base_names,
            "decorators": decorators,
            "method_ids": method_ids
        }, sort_keys=True)

    return nodes, contains_edges


def _extract_methods_from_class(
    repo_id: str,
    file_record: FileRecord,
    class_node_id: str,
    class_qualified_name: str,
    class_node: ast.ClassDef,
    scope_tracker: ScopeTracker,
    duplicate_tracker: DuplicateTracker,
    module_path: str,
    file_text: str,
) -> tuple[list[dict], list[dict]]:
    """Extract methods from a class body.

    Args:
        repo_id: Repository ID.
        file_record: File record.
        class_node_id: Class node ID.
        class_qualified_name: Class qualified name.
        class_node: AST ClassDef node.
        scope_tracker: Scope tracker.
        duplicate_tracker: Duplicate tracker for symbol ID disambiguation.
        module_path: Module path.

    Returns:
        Tuple of (method nodes list, contains edges list).
    """
    # Import here to avoid circular import
    extract_callable_nodes = repo_context.parsing.callable_extractor.extract_callable_nodes

    methods = []
    contains_edges = []

    # Use context manager to ensure stack stays balanced
    with scope_tracker.scope_context(class_node_id, class_node.name, "class"):
        # Extract methods
        for stmt in class_node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_nodes = extract_callable_nodes(
                    repo_id=repo_id,
                    file_record=file_record,
                    parent_id=class_node_id,
                    parent_qualified_name=class_qualified_name,
                    nodes=[stmt],
                    scope_tracker=scope_tracker,
                    duplicate_tracker=duplicate_tracker,
                    module_path=module_path,
                    file_text=file_text,
                )
                methods.extend(method_nodes)
                
                # Create contains edge for each method
                for method_node in method_nodes:
                    contains_edges.append({
                        "id": f"edge:{repo_id}:contains:{class_node_id}->{method_node['id']}",
                        "repo_id": repo_id,
                        "kind": "contains",
                        "from_id": class_node_id,
                        "to_id": method_node["id"],
                        "source": "python-ast",
                        "confidence": 1.0,
                        "evidence_file_id": file_record.id,
                        "evidence_uri": file_record.uri,
                        "evidence_range_json": None,
                        "payload_json": "{}",
                        "last_indexed_at": file_record.last_indexed_at,
                    })

    return methods, contains_edges


def _compute_class_semantic_hash(qualified_name: str, base_names: list[str], decorators: list[str]) -> str:
    """Compute a semantic hash for a class node.

    Args:
        qualified_name: Class qualified name.
        base_names: List of base class names.
        decorators: List of decorator strings.

    Returns:
        SHA-256 hash with prefix.
    """

    hash_obj = hashlib.sha256()
    hash_obj.update("kind:class".encode())
    hash_obj.update(f"qualified_name:{qualified_name}".encode())
    hash_obj.update(f"bases:{sorted(base_names)}".encode())
    hash_obj.update(f"decorators:{sorted(decorators)}".encode())

    return f"sha256:{hash_obj.hexdigest()}"
