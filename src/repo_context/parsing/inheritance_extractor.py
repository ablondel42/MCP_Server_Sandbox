"""Inheritance edge extraction from Python AST."""

import ast
import json

from repo_context.models.file import FileRecord


def extract_inheritance_edges(
    repo_id: str,
    file_record: FileRecord,
    class_nodes: list[dict],
    tree: ast.Module,
) -> list[dict]:
    """Extract inheritance edges for class definitions.
    
    Args:
        repo_id: Repository ID.
        file_record: File record from Phase 2.
        class_nodes: List of extracted class node dicts.
        tree: Parsed AST module.
        
    Returns:
        List of inheritance edge dictionaries.
    """
    edges = []
    
    # Build a map of class node ID to class AST node for lookup
    class_ast_map = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_ast_map[node.name] = node
    
    # Process each class node
    for class_node in class_nodes:
        class_name = class_node["name"]
        class_node_id = class_node["id"]
        
        # Find the corresponding AST node
        ast_node = class_ast_map.get(class_name)
        if ast_node is None:
            continue
        
        # Create an inherits edge for each base
        for base in ast_node.bases:
            try:
                base_name = ast.unparse(base)
            except Exception:
                base_name = "<unparsable>"
            
            to_id = f"unresolved_base:{base_name}"
            edge_id = _make_inherits_edge_id(repo_id, class_node_id, base_name)
            
            edges.append({
                "id": edge_id,
                "repo_id": repo_id,
                "kind": "inherits",
                "from_id": class_node_id,
                "to_id": to_id,
                "source": "python-ast",
                "confidence": 0.75,
                "evidence_file_id": file_record.id,
                "evidence_uri": file_record.uri,
                "evidence_range_json": json.dumps(_make_range_from_node(base), sort_keys=True) if _make_range_from_node(base) else None,
                "payload_json": json.dumps({
                    "base_name": base_name
                }, sort_keys=True),
                "last_indexed_at": file_record.last_indexed_at,
            })
    
    return edges


def _make_inherits_edge_id(repo_id: str, class_node_id: str, base_name: str) -> str:
    """Create a deterministic edge ID for an inheritance edge.
    
    Args:
        repo_id: Repository ID.
        class_node_id: Class node ID.
        base_name: Base class name.
        
    Returns:
        Deterministic edge ID.
    """
    return f"edge:{repo_id}:inherits:{class_node_id}->unresolved_base:{base_name}"


def _make_range_from_node(node: ast.AST) -> dict | None:
    """Create a range dict from an AST node.
    
    Args:
        node: AST node.
        
    Returns:
        Range dict or None if metadata missing.
    """
    lineno = getattr(node, "lineno", None)
    col_offset = getattr(node, "col_offset", None)
    end_lineno = getattr(node, "end_lineno", None)
    end_col_offset = getattr(node, "end_col_offset", None)
    
    if lineno is None or col_offset is None:
        return None
    
    # Convert to zero-based
    start_line = lineno - 1 if lineno else None
    end_line = end_lineno - 1 if end_lineno else None
    
    return {
        "start": {"line": start_line, "character": col_offset},
        "end": {"line": end_line, "character": end_col_offset}
    }
