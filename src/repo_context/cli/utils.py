"""CLI main entry point."""

import argparse

from repo_context.config import get_config
from repo_context.logging_config import get_logger
from repo_context.storage import (
    get_connection,
    initialize_database,
)
from dataclasses import asdict
import typing

logger = get_logger("cli.main")





def _node_to_dict(node) -> dict:
    """Convert a node to a dictionary.

    Args:
        node: Node dict or object.

    Returns:
        Dictionary representation.
    """
    if isinstance(node, dict):
        return node
    return asdict(node)



def _context_to_dict(context) -> dict:
    """Convert SymbolContext to dict.

    Args:
        context: SymbolContext instance or dict.

    Returns:
        Dictionary representation.
    """
    if isinstance(context, dict):
        return context
    # Handle Pydantic model
    if hasattr(context, "model_dump"):
        return context.model_dump()
    # Handle dataclass
    return asdict(context)



def _make_dict_json_serializable(d: dict) -> dict:
    """Recursively convert sets in a dict to sorted lists for JSON serialization.

    Args:
        d: Dictionary that may contain sets.

    Returns:
        Dictionary with all sets converted to sorted lists.
    """
    result: typing.Any = {}
    for k, v in d.items():
        if isinstance(v, set):
            result[k] = sorted(v)
        elif isinstance(v, dict):
            result[k] = _make_dict_json_serializable(v)
        elif isinstance(v, list):
            result[k] = [
                _make_dict_json_serializable(item) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            result[k] = v
    return result



def _risk_to_dict(risk_result) -> dict:
    """Convert RiskResult to dict.

    Args:
        risk_result: RiskResult instance or dict.

    Returns:
        Dictionary representation (JSON-serializable).
    """
    if isinstance(risk_result, dict):
        return _make_dict_json_serializable(risk_result)
    # Handle Pydantic model
    if hasattr(risk_result, "model_dump"):
        return _make_dict_json_serializable(risk_result.model_dump())
    # Handle dataclass
    return _make_dict_json_serializable(asdict(risk_result))



def _adapt_node_for_mcp(node: dict) -> dict:
    """Adapt a node dict for MCP output.

    Args:
        node: Node dictionary.

    Returns:
        Adapted node for MCP.
    """
    return {
        "id": node.get("id"),
        "kind": node.get("kind"),
        "qualified_name": node.get("qualified_name"),
        "name": node.get("name"),
        "file_id": node.get("file_id"),
        "parent_id": node.get("parent_id"),
        "lexical_parent_id": node.get("lexical_parent_id"),
        "visibility_hint": node.get("visibility_hint"),
        "doc_summary": node.get("doc_summary"),
    }



def adapt_context(context_dict: dict) -> dict:
    """Adapt context dict for MCP output.

    Args:
        context_dict: Context dictionary.

    Returns:
        Adapted context for MCP.
    """
    focus = context_dict.get("focus_symbol", {})
    return {
        "focus_symbol": _adapt_node_for_mcp(focus),
        "structural_parent": _adapt_node_for_mcp(context_dict.get("structural_parent", {})) if context_dict.get("structural_parent") else None,
        "structural_children": [_adapt_node_for_mcp(c) for c in context_dict.get("structural_children", [])],
        "lexical_parent": _adapt_node_for_mcp(context_dict.get("lexical_parent", {})) if context_dict.get("lexical_parent") else None,
        "lexical_children": [_adapt_node_for_mcp(c) for c in context_dict.get("lexical_children", [])],
        "incoming_edges": context_dict.get("incoming_edges", []),
        "outgoing_edges": context_dict.get("outgoing_edges", []),
        "structural_summary": context_dict.get("structural_summary", {}),
        "freshness": context_dict.get("freshness", {}),
        "confidence": context_dict.get("confidence", {}),
    }



def adapt_risk_result(risk_dict: dict) -> dict:
    """Adapt risk result dict for MCP output.

    Args:
        risk_dict: Risk result dictionary.

    Returns:
        Adapted risk result for MCP.
    """
    return {
        "risk_score": risk_dict.get("risk_score"),
        "decision": risk_dict.get("decision"),
        "issues": risk_dict.get("issues", []),
        "facts": risk_dict.get("facts", {}),
    }



def adapt_references(ref_edges: list, ref_stats: dict) -> dict:
    """Adapt references for MCP output.

    Args:
        ref_edges: List of reference edge dicts.
        ref_stats: Reference statistics.

    Returns:
        Adapted references for MCP.
    """
    return {
        "references": ref_edges,
        "reference_summary": {
            "count": ref_stats.get("count", 0),
            "available": ref_stats.get("available", True),
            "referencing_files": ref_stats.get("file_count", 0),
            "referencing_modules": ref_stats.get("module_count", 0),
        },
    }



def get_connection_for_args(args: argparse.Namespace):
    """Get a database connection from CLI args.

    Args:
        args: Parsed command line arguments.

    Returns:
        Initialized SQLite connection.
    """
    config = get_config()
    db_path = args.db_path if hasattr(args, 'db_path') and args.db_path else config.db_path
    conn = get_connection(db_path)
    initialize_database(conn)
    return conn
