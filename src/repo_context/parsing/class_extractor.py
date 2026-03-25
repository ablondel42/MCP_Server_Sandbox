"""Class node extraction from Python AST."""

import ast
import json

from repo_context.models.file import FileRecord
from repo_context.parsing.naming import build_class_node_id, build_class_qualified_name
from repo_context.parsing.ranges import make_range, make_name_selection_range
from repo_context.parsing.docstrings import get_doc_summary


def extract_class_nodes(
    repo_id: str,
    file_record: FileRecord,
    module_node_id: str,
    module_path: str,
    tree: ast.Module,
) -> list[dict]:
    """Extract class nodes from top-level class definitions.
    
    Args:
        repo_id: Repository ID.
        file_record: File record from Phase 2.
        module_node_id: Parent module node ID.
        module_path: Module path for qualified name building.
        tree: Parsed AST module.
        
    Returns:
        List of class node dictionaries ready for persistence.
    """
    nodes = []
    
    # Only process top-level classes in tree.body
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        
        class_name = node.name
        qualified_name = build_class_qualified_name(module_path, class_name)
        node_id = build_class_node_id(repo_id, qualified_name)
        
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
            "parent_id": module_node_id,
            "visibility_hint": visibility_hint,
            "doc_summary": get_doc_summary(node),
            "content_hash": "",
            "semantic_hash": _compute_class_semantic_hash(qualified_name, base_names, decorators),
            "source": "python-ast",
            "confidence": 1.0,
            "payload_json": json.dumps({
                "base_names": base_names,
                "decorators": decorators,
                "method_ids": []
            }, sort_keys=True),
            "last_indexed_at": file_record.last_indexed_at,
        })
    
    return nodes


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
