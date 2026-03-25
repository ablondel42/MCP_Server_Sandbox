"""Class node extraction from Python AST."""

import ast
import json
from typing import Optional

from repo_context.models.file import FileRecord
from repo_context.parsing.naming import (
    build_class_node_id,
    build_class_qualified_name,
    build_nested_qualified_name,
    build_disambiguated_symbol_id,
)
from repo_context.parsing.ranges import make_range, make_name_selection_range
from repo_context.parsing.docstrings import get_doc_summary
from repo_context.parsing.scope_tracker import ScopeTracker


def extract_class_nodes(
    repo_id: str,
    file_record: FileRecord,
    module_node_id: str,
    module_path: str,
    tree: ast.Module,
    scope_tracker: ScopeTracker,
    parent_id: Optional[str] = None,
) -> list[dict]:
    """Extract class nodes from class definitions.

    Args:
        repo_id: Repository ID.
        file_record: File record from Phase 2.
        module_node_id: Parent module node ID (for module-level classes).
        module_path: Module path for qualified name building.
        tree: Parsed AST module.
        scope_tracker: Scope tracker for lexical nesting.
        parent_id: Optional parent ID (for nested classes).

    Returns:
        List of class node dictionaries ready for persistence.
    """
    nodes = []

    # Only process top-level classes in tree.body
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue

        class_name = node.name
        
        # Determine scope based on current tracker state
        current_scope = scope_tracker.get_current_scope()
        lexical_parent_id = scope_tracker.get_lexical_parent_id()
        
        # Build qualified name using lexical chain for nested classes
        if scope_tracker.is_empty():
            qualified_name = build_class_qualified_name(module_path, class_name)
        else:
            lexical_chain = scope_tracker.get_lexical_chain()
            qualified_name = build_nested_qualified_name(module_path, lexical_chain, class_name)
        
        # Check for duplicate same-scope declarations
        lineno = getattr(node, "lineno", None)
        col = getattr(node, "col_offset", None)
        
        # Build symbol ID (with disambiguation if needed)
        base_id = build_class_node_id(repo_id, qualified_name)
        if lineno is not None and col is not None:
            node_id = build_disambiguated_symbol_id(repo_id, "class", qualified_name, lineno, col)
        else:
            node_id = base_id

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

        nodes.append({
            "id": node_id,
            "repo_id": repo_id,
            "file_id": file_record.id,
            "language": "python",
            "kind": "class",
            "name": class_name,
            "qualified_name": qualified_name,
            "uri": file_record.uri,
            "range_json": json.dumps(make_range(node), sort_keys=True) if make_range(node) else None,
            "selection_range_json": json.dumps(make_name_selection_range(node), sort_keys=True) if make_name_selection_range(node) else None,
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
        })

        # Recursively extract methods from class body
        method_nodes = _extract_methods_from_class(
            repo_id, file_record, node_id, qualified_name, node, scope_tracker, module_path
        )
        nodes.extend(method_nodes)

    return nodes


def _extract_methods_from_class(
    repo_id: str,
    file_record: FileRecord,
    class_node_id: str,
    class_qualified_name: str,
    class_node: ast.ClassDef,
    scope_tracker: ScopeTracker,
    module_path: str,
) -> list[dict]:
    """Extract methods from a class body.
    
    Args:
        repo_id: Repository ID.
        file_record: File record.
        class_node_id: Class node ID.
        class_qualified_name: Class qualified name.
        class_node: AST ClassDef node.
        scope_tracker: Scope tracker.
        module_path: Module path.
        
    Returns:
        List of method node dicts.
    """
    # Import here to avoid circular import
    from repo_context.parsing.callable_extractor import extract_callable_nodes
    
    methods = []
    
    # Push class onto scope stack
    scope_tracker.push_declaration(class_node_id, class_node.name, "class")
    
    # Extract methods
    for stmt in class_node.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.extend(extract_callable_nodes(
                repo_id=repo_id,
                file_record=file_record,
                parent_id=class_node_id,
                parent_qualified_name=class_qualified_name,
                nodes=[stmt],
                scope_tracker=scope_tracker,
                module_path=module_path,
            ))
    
    # Pop class from scope stack
    scope_tracker.pop_declaration()
    
    return methods


def _compute_class_semantic_hash(qualified_name: str, base_names: list[str], decorators: list[str]) -> str:
    """Compute a semantic hash for a class node.

    Args:
        qualified_name: Class qualified name.
        base_names: List of base class names.
        decorators: List of decorator strings.

    Returns:
        SHA-256 hash with prefix.
    """
    import hashlib

    hash_obj = hashlib.sha256()
    hash_obj.update(f"kind:class".encode())
    hash_obj.update(f"qualified_name:{qualified_name}".encode())
    hash_obj.update(f"bases:{sorted(base_names)}".encode())
    hash_obj.update(f"decorators:{sorted(decorators)}".encode())

    return f"sha256:{hash_obj.hexdigest()}"
