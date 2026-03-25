"""Callable node extraction from Python AST."""

import ast
import json

from repo_context.models.file import FileRecord
from repo_context.parsing.naming import build_callable_node_id, build_callable_qualified_name
from repo_context.parsing.ranges import make_range, make_name_selection_range
from repo_context.parsing.docstrings import get_doc_summary


def extract_callable_nodes(
    repo_id: str,
    file_record: FileRecord,
    parent_id: str,
    parent_qualified_name: str,
    nodes: list[ast.AST],
    is_method: bool,
) -> list[dict]:
    """Extract callable nodes from function/method definitions.
    
    Args:
        repo_id: Repository ID.
        file_record: File record from Phase 2.
        parent_id: Parent node ID (module or class).
        parent_qualified_name: Parent qualified name for building callable qualified name.
        nodes: List of AST nodes to process (FunctionDef or AsyncFunctionDef).
        is_method: True if extracting methods, False if extracting top-level functions.
        
    Returns:
        List of callable node dictionaries ready for persistence.
    """
    extracted = []
    
    for node in nodes:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        
        callable_name = node.name
        is_async = isinstance(node, ast.AsyncFunctionDef)
        
        # Determine kind
        if is_async:
            kind = "async_method" if is_method else "async_function"
        else:
            kind = "method" if is_method else "function"
        
        qualified_name = build_callable_qualified_name(parent_qualified_name, callable_name)
        node_id = build_callable_node_id(repo_id, kind, qualified_name)
        
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
        
        extracted.append({
            "id": node_id,
            "repo_id": repo_id,
            "file_id": file_record.id,
            "language": "python",
            "kind": kind,
            "name": callable_name,
            "qualified_name": qualified_name,
            "uri": file_record.uri,
            "range_json": json.dumps(make_range(node), sort_keys=True) if make_range(node) else None,
            "selection_range_json": json.dumps(make_name_selection_range(node), sort_keys=True) if make_name_selection_range(node) else None,
            "parent_id": parent_id,
            "visibility_hint": visibility_hint,
            "doc_summary": get_doc_summary(node),
            "content_hash": "",
            "semantic_hash": _compute_callable_semantic_hash(qualified_name, kind, parameters, return_annotation, decorators, is_async),
            "source": "python-ast",
            "confidence": 1.0,
            "payload_json": json.dumps({
                "parameters": parameters,
                "return_annotation": return_annotation,
                "decorators": decorators,
                "is_async": is_async,
                "is_method": is_method,
                "is_generator": is_generator
            }, sort_keys=True),
            "last_indexed_at": file_record.last_indexed_at,
        })
    
    return extracted


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
