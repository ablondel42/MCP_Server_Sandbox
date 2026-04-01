"""Callable node extraction from Python AST."""

import ast
import json
from typing import Optional

from repo_context.models.file import FileRecord
from repo_context.parsing.naming import (
    build_callable_qualified_name,
    build_nested_qualified_name,
    DuplicateTracker,
)
from repo_context.parsing.ranges import make_range, make_name_selection_range
from repo_context.parsing.docstrings import get_doc_summary
from repo_context.parsing.scope_tracker import ScopeTracker


def extract_callable_nodes(
    repo_id: str,
    file_record: FileRecord,
    parent_id: str,
    parent_qualified_name: str,
    nodes: list[ast.AST],
    scope_tracker: ScopeTracker,
    duplicate_tracker: DuplicateTracker,
    module_path: str,
    file_text: str,
) -> list[dict]:
    """Extract callable nodes from function/method definitions with nested scope support.

    Args:
        repo_id: Repository ID.
        file_record: File record from Phase 2.
        parent_id: Parent node ID (module or class).
        parent_qualified_name: Parent qualified name for building callable qualified name.
        nodes: List of AST nodes to process (FunctionDef or AsyncFunctionDef).
        scope_tracker: Scope tracker for lexical nesting.
        duplicate_tracker: Duplicate tracker for symbol ID disambiguation.
        module_path: Module path for qualified name building.

    Returns:
        List of callable node dictionaries ready for persistence.
    """
    extracted = []

    for node in nodes:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        callable_name = node.name
        is_async = isinstance(node, ast.AsyncFunctionDef)

        # Determine scope and kind based on current tracker state
        current_scope = scope_tracker.get_current_scope()
        lexical_parent_id = scope_tracker.get_lexical_parent_id()

        # Classify kind based on scope
        if current_scope == "module":
            # Module-level: function or async_function
            kind = "async_function" if is_async else "function"
        elif current_scope == "class":
            # Class body: method or async_method
            kind = "async_method" if is_async else "method"
        else:
            # Function scope: local_function or local_async_function
            kind = "local_async_function" if is_async else "local_function"

        # Build qualified name using lexical chain for nested callables
        if scope_tracker.is_empty():
            qualified_name = build_callable_qualified_name(parent_qualified_name, callable_name)
        else:
            lexical_chain = scope_tracker.get_lexical_chain()
            qualified_name = build_nested_qualified_name(module_path, lexical_chain, callable_name)

        # Build symbol ID using duplicate tracker
        node_id = duplicate_tracker.get_symbol_id(repo_id, kind, qualified_name)

        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            try:
                decorators.append(ast.unparse(decorator))
            except Exception:
                decorators.append("<unparsable>")

        # Extract parameters
        parameters = extract_parameters(node.args)

        # Extract return annotation
        return_annotation = None
        if node.returns is not None:
            try:
                return_annotation = ast.unparse(node.returns)
            except Exception:
                return_annotation = "<unparsable>"

        # Check if generator
        is_generator = _is_generator(node)

        # Determine visibility
        if callable_name.startswith("_") and not (callable_name.startswith("__") and callable_name.endswith("__")):
            visibility_hint = "private_like"
        else:
            visibility_hint = "public"

        # Get source line for precise name positioning
        lines = file_text.splitlines()
        source_line = lines[node.lineno - 1] if node.lineno and node.lineno <= len(lines) else None
        
        extracted.append({
            "id": node_id,
            "repo_id": repo_id,
            "file_id": file_record.id,
            "language": "python",
            "kind": kind,
            "name": callable_name,
            "qualified_name": qualified_name,
            "uri": file_record.uri,
            "range_json": make_range(node) if make_range(node) else None,
            "selection_range_json": make_name_selection_range(node, source_line) if make_name_selection_range(node, source_line) else None,
            "parent_id": lexical_parent_id,
            "visibility_hint": visibility_hint,
            "doc_summary": get_doc_summary(node),
            "content_hash": "",
            "semantic_hash": _compute_callable_semantic_hash(qualified_name, kind, parameters, return_annotation, decorators, is_async),
            "source": "python-ast",
            "confidence": 1.0,
            "scope": current_scope,
            "lexical_parent_id": lexical_parent_id,
            "payload_json": json.dumps({
                "parameters": parameters,
                "return_annotation": return_annotation,
                "decorators": decorators,
                "is_async": is_async,
                "is_method": current_scope == "class",
                "is_generator": is_generator
            }, sort_keys=True),
            "last_indexed_at": file_record.last_indexed_at,
        })

        # Recursively extract nested declarations from function body
        nested_nodes = _extract_nested_declarations(
            repo_id, file_record, node_id, qualified_name, node, scope_tracker, duplicate_tracker, module_path, file_text
        )
        extracted.extend(nested_nodes)

    return extracted


def _extract_nested_declarations(
    repo_id: str,
    file_record: FileRecord,
    parent_id: str,
    parent_qualified_name: str,
    func_node: ast.AST,
    scope_tracker: ScopeTracker,
    duplicate_tracker: DuplicateTracker,
    module_path: str,
    file_text: str,
) -> list[dict]:
    """Extract nested declarations from a function body.
    
    Args:
        repo_id: Repository ID.
        file_record: File record.
        parent_id: Parent function node ID.
        parent_qualified_name: Parent function qualified name.
        func_node: AST FunctionDef or AsyncFunctionDef node.
        scope_tracker: Scope tracker for lexical nesting.
        duplicate_tracker: Duplicate tracker for symbol ID disambiguation.
        module_path: Module path.
        
    Returns:
        List of nested declaration nodes.
    """
    # Import here to avoid circular import
    from repo_context.parsing.class_extractor import extract_class_nodes

    nested = []

    # Determine kind for scope tracker
    is_async = isinstance(func_node, ast.AsyncFunctionDef)
    current_scope = scope_tracker.get_current_scope()

    if current_scope == "module":
        kind = "async_function" if is_async else "function"
    elif current_scope == "class":
        kind = "async_method" if is_async else "method"
    else:
        kind = "local_async_function" if is_async else "local_function"

    # Use context manager to ensure stack stays balanced
    with scope_tracker.scope_context(parent_id, func_node.name, "function"):
        # Build qualified name for this function (using parent's qualified name, not scope tracker)
        if parent_qualified_name:
            func_qualified_name = f"{parent_qualified_name}.{func_node.name}"
        else:
            func_qualified_name = f"{module_path}.{func_node.name}"
        
        # Extract nested declarations from function body
        for stmt in func_node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Extract nested function
                nested.extend(extract_callable_nodes(
                    repo_id=repo_id,
                    file_record=file_record,
                    parent_id=parent_id,
                    parent_qualified_name=func_qualified_name,
                    nodes=[stmt],
                    scope_tracker=scope_tracker,
                    duplicate_tracker=duplicate_tracker,
                    module_path=module_path,
                    file_text=file_text,
                ))
            elif isinstance(stmt, ast.ClassDef):
                # Extract nested class
                nested_class_nodes, _ = extract_class_nodes(
                    repo_id=repo_id,
                    file_record=file_record,
                    module_node_id=parent_id,
                    module_path=module_path,
                    tree=ast.Module(body=[stmt], type_ignores=[]),
                    scope_tracker=scope_tracker,
                    duplicate_tracker=duplicate_tracker,
                    parent_id=parent_id,
                    parent_qualified_name=func_qualified_name,
                    file_text=file_text,
                )
                nested.extend(nested_class_nodes)

    return nested


def extract_parameters(args: ast.arguments) -> list[dict]:
    """Extract parameter information from ast.arguments.

    Args:
        args: AST arguments node.

    Returns:
        List of parameter dictionaries.
    """
    parameters = []

    # Positional-only args
    for arg in getattr(args, "posonlyargs", []):
        annotation = None
        if arg.annotation is not None:
            try:
                annotation = ast.unparse(arg.annotation)
            except Exception:
                annotation = "<unparsable>"
        parameters.append({
            "name": arg.arg,
            "kind": "positional_only",
            "annotation": annotation,
            "default_value_hint": None,
        })

    # Regular args
    for arg in args.args:
        annotation = None
        if arg.annotation is not None:
            try:
                annotation = ast.unparse(arg.annotation)
            except Exception:
                annotation = "<unparsable>"
        parameters.append({
            "name": arg.arg,
            "kind": "positional_or_keyword",
            "annotation": annotation,
            "default_value_hint": None,
        })

    # *args
    if args.vararg is not None:
        annotation = None
        if args.vararg.annotation is not None:
            try:
                annotation = ast.unparse(args.vararg.annotation)
            except Exception:
                annotation = "<unparsable>"
        parameters.append({
            "name": args.vararg.arg,
            "kind": "var_positional",
            "annotation": annotation,
            "default_value_hint": None,
        })

    # Keyword-only args
    for arg in args.kwonlyargs:
        annotation = None
        if arg.annotation is not None:
            try:
                annotation = ast.unparse(arg.annotation)
            except Exception:
                annotation = "<unparsable>"
        parameters.append({
            "name": arg.arg,
            "kind": "keyword_only",
            "annotation": annotation,
            "default_value_hint": None,
        })

    # **kwargs
    if args.kwarg is not None:
        annotation = None
        if args.kwarg.annotation is not None:
            try:
                annotation = ast.unparse(args.kwarg.annotation)
            except Exception:
                annotation = "<unparsable>"
        parameters.append({
            "name": args.kwarg.arg,
            "kind": "var_keyword",
            "annotation": annotation,
            "default_value_hint": None,
        })

    return parameters


def _is_generator(node: ast.AST) -> bool:
    """Check if a function node is a generator.

    Args:
        node: AST node to check.

    Returns:
        True if the function contains yield expressions.
    """
    for child in ast.walk(node):
        if isinstance(child, (ast.Yield, ast.YieldFrom)):
            return True
    return False


def _compute_callable_semantic_hash(
    qualified_name: str,
    kind: str,
    parameters: list[dict],
    return_annotation: str | None,
    decorators: list[str],
    is_async: bool,
) -> str:
    """Compute a semantic hash for a callable node.

    Args:
        qualified_name: Callable qualified name.
        kind: Callable kind.
        parameters: List of parameter dicts.
        return_annotation: Return annotation string.
        decorators: List of decorator strings.
        is_async: Whether the callable is async.

    Returns:
        SHA-256 hash with prefix.
    """
    import hashlib

    hash_obj = hashlib.sha256()
    hash_obj.update(f"kind:{kind}".encode())
    hash_obj.update(f"qualified_name:{qualified_name}".encode())
    hash_obj.update(f"is_async:{is_async}".encode())

    # Parameter names and kinds
    param_data = [(p["name"], p["kind"]) for p in parameters]
    hash_obj.update(f"parameters:{sorted(param_data)}".encode())

    hash_obj.update(f"return:{return_annotation}".encode())
    hash_obj.update(f"decorators:{sorted(decorators)}".encode())

    return f"sha256:{hash_obj.hexdigest()}"
