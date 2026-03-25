"""Import extraction from Python AST."""

import ast
import json

from repo_context.models.file import FileRecord


def extract_import_edges_and_payload(
    repo_id: str,
    module_node_id: str,
    file_record: FileRecord,
    tree: ast.Module,
) -> tuple[list[dict], list[str], list[str]]:
    """Extract import edges and module payload data from AST.
    
    Args:
        repo_id: Repository ID.
        module_node_id: Module node ID.
        file_record: File record from Phase 2.
        tree: Parsed AST module.
        
    Returns:
        Tuple of (list of import edges, list of imported modules, list of imported symbols).
    """
    edges = []
    imported_modules = []
    imported_symbols = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # Handle: import module1, module2, ...
            for alias in node.names:
                module_name = alias.name
                imported_modules.append(module_name)
                
                # Create edge to unresolved target
                to_id = f"external_or_unresolved:{module_name}"
                edge_id = _make_import_edge_id(repo_id, module_node_id, to_id, getattr(node, "lineno", 0))
                
                edges.append({
                    "id": edge_id,
                    "repo_id": repo_id,
                    "kind": "imports",
                    "from_id": module_node_id,
                    "to_id": to_id,
                    "source": "python-ast",
                    "confidence": 0.8,
                    "evidence_file_id": file_record.id,
                    "evidence_uri": file_record.uri,
                    "evidence_range_json": json.dumps(_make_range_from_node(node), sort_keys=True) if _make_range_from_node(node) else None,
                    "payload_json": json.dumps({
                        "alias": alias.asname,
                        "module": module_name,
                        "level": 0,
                        "import_type": "import"
                    }, sort_keys=True),
                    "last_indexed_at": file_record.last_indexed_at,
                })
        
        elif isinstance(node, ast.ImportFrom):
            # Handle: from module import symbol1, symbol2, ...
            module_name = node.module or ""
            level = node.level  # For relative imports
            
            if module_name:
                imported_modules.append(module_name)
            
            for alias in node.names:
                symbol_name = alias.name
                imported_symbols.append(symbol_name)
                
                # Build target
                if module_name:
                    target = f"{module_name}.{symbol_name}"
                else:
                    target = symbol_name
                
                to_id = f"external_or_unresolved:{target}"
                edge_id = _make_import_edge_id(repo_id, module_node_id, to_id, getattr(node, "lineno", 0))
                
                edges.append({
                    "id": edge_id,
                    "repo_id": repo_id,
                    "kind": "imports",
                    "from_id": module_node_id,
                    "to_id": to_id,
                    "source": "python-ast",
                    "confidence": 0.8,
                    "evidence_file_id": file_record.id,
                    "evidence_uri": file_record.uri,
                    "evidence_range_json": json.dumps(_make_range_from_node(node), sort_keys=True) if _make_range_from_node(node) else None,
                    "payload_json": json.dumps({
                        "alias": alias.asname,
                        "module": module_name,
                        "level": level,
                        "import_type": "from"
                    }, sort_keys=True),
                    "last_indexed_at": file_record.last_indexed_at,
                })
    
    return edges, imported_modules, imported_symbols


def _make_import_edge_id(repo_id: str, from_id: str, to_id: str, lineno: int) -> str:
    """Create a deterministic edge ID for an import edge.
    
    Args:
        repo_id: Repository ID.
        from_id: Source module node ID.
        to_id: Target unresolved ID.
        lineno: Line number for uniqueness.
        
    Returns:
        Deterministic edge ID.
    """
    return f"edge:{repo_id}:imports:{from_id}->{to_id}:{lineno}"


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
