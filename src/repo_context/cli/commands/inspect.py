"""CLI main entry point."""

import argparse
import asyncio
import json
import sys
import typing

from repo_context.logging_config import get_logger
from repo_context.storage import (
    close_connection,
    get_node_by_id,
    get_file_by_id,
)
from repo_context.graph import (
    get_symbol_by_qualified_name,
    build_reference_stats,
    list_reference_edges_for_target,
    list_referenced_by,
    list_references_from_symbol,
    analyze_symbol_risk,
    analyze_target_set_risk,
)
from repo_context.context import build_symbol_context



from ..utils import _node_to_dict, _context_to_dict, _risk_to_dict, adapt_context, adapt_risk_result, adapt_references, get_connection_for_args
from repo_context.mcp.tools import (
    resolve_symbol,
    get_symbol_context,
    get_symbol_references,
)
from repo_context.mcp.tools import analyze_symbol_risk as mcp_analyze_symbol_risk



logger = get_logger("cli.main")

def cmd_inspect_file(args: argparse.Namespace) -> int:
    """Inspect tracked file metadata.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    conn = get_connection_for_args(args)
    try:
        file_path = args.file_path
        file_record = get_file_by_id(conn, f"file:{file_path}")

        if file_record is None:
            print(f"File not found: {file_path}", file=sys.stderr)
            return 1

        # Handle both dict and object
        if isinstance(file_record, dict):
            data = {
                "id": file_record["id"],
                "repo_id": file_record["repo_id"],
                "file_path": file_record["file_path"],
                "uri": file_record["uri"],
                "module_path": file_record["module_path"],
                "language": file_record["language"],
                "content_hash": file_record["content_hash"],
                "size_bytes": file_record["size_bytes"],
                "last_modified_at": file_record["last_modified_at"],
                "last_indexed_at": file_record["last_indexed_at"],
            }
        else:
            data = {
                "id": file_record.id,
                "repo_id": file_record.repo_id,
                "file_path": file_record.file_path,
                "uri": file_record.uri,
                "module_path": file_record.module_path,
                "language": file_record.language,
                "content_hash": file_record.content_hash,
                "size_bytes": file_record.size_bytes,
                "last_modified_at": file_record.last_modified_at,
                "last_indexed_at": file_record.last_indexed_at,
            }

        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(f"\nFile: {file_path}")
            print(f"  ID: {data['id']}")
            print(f"  URI: {data['uri']}")
            print(f"  Module: {data['module_path']}")
            print(f"  Size: {data['size_bytes']} bytes")
            print(f"  Hash: {data['content_hash']}")
            print(f"  Last indexed: {data['last_indexed_at']}")
        return 0
    except Exception as exc:
        logger.exception("cmd_inspect_file: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)



def cmd_inspect_node(args: argparse.Namespace) -> int:
    """Inspect a stored node payload.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    conn = get_connection_for_args(args)
    try:
        node_id = args.node_id
        node = get_node_by_id(conn, node_id)

        if node is None:
            print(f"Node not found: {node_id}", file=sys.stderr)
            return 1

        data = _node_to_dict(node)

        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(f"\nNode: {node_id}")
            print(f"  Kind: {data.get('kind')}")
            print(f"  Qualified name: {data.get('qualified_name')}")
            print(f"  File: {data.get('file_id')}")
            print(f"  Parent: {data.get('parent_id')}")
        return 0
    except Exception as exc:
        logger.exception("cmd_inspect_node: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)



def cmd_inspect_edge(args: argparse.Namespace) -> int:
    """Inspect a stored edge payload.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    conn = get_connection_for_args(args)
    try:
        edge_id = args.edge_id
        cursor = conn.execute(
            "SELECT * FROM edges WHERE id = ?",
            (edge_id,),
        )
        row = cursor.fetchone()

        if row is None:
            print(f"Edge not found: {edge_id}", file=sys.stderr)
            return 1

        data = dict(row)

        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(f"\nEdge: {edge_id}")
            print(f"  Kind: {data.get('kind')}")
            print(f"  From: {data.get('from_id')}")
            print(f"  To: {data.get('to_id')}")
            print(f"  Source: {data.get('source')}")
        return 0
    except Exception as exc:
        logger.exception("cmd_inspect_edge: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)



def cmd_inspect_graph_for_file(args: argparse.Namespace) -> int:
    """List nodes and edges owned by one file.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    conn = get_connection_for_args(args)
    try:
        file_id = f"file:{args.file_path}"
        kinds = getattr(args, "kinds", None)

        # Get nodes for file
        if kinds:
            placeholders = ",".join("?" * len(kinds))
            cursor = conn.execute(
                f"SELECT * FROM nodes WHERE file_id = ? AND kind IN ({placeholders})",
                [file_id] + kinds,
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM nodes WHERE file_id = ?",
                (file_id,),
            )
        nodes = [dict(r) for r in cursor.fetchall()]

        # Get edges for file
        cursor = conn.execute(
            "SELECT * FROM edges WHERE evidence_file_id = ?",
            (file_id,),
        )
        edges = [dict(r) for r in cursor.fetchall()]

        data = {
            "file_id": file_id,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }

        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(f"\nGraph for file: {args.file_path}")
            print(f"  Nodes: {len(nodes)}")
            print(f"  Edges: {len(edges)}")
        return 0
    except Exception as exc:
        logger.exception("cmd_inspect_graph_for_file: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)



def cmd_inspect_context(args: argparse.Namespace) -> int:
    """Inspect symbol context.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    conn = get_connection_for_args(args)
    try:
        symbol_id = args.symbol_id
        context = build_symbol_context(conn, symbol_id)
        data = _context_to_dict(context)

        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(f"\nContext: {data['focus_symbol']['qualified_name']}")
            print(f"  Kind: {data['focus_symbol']['kind']}")
            print(f"  Parent: {data.get('structural_parent', {}).get('qualified_name', 'None')}")
            print(f"  Children: {len(data.get('structural_children', []))}")
            print(f"  Incoming edges: {len(data.get('incoming_edges', []))}")
            print(f"  Outgoing edges: {len(data.get('outgoing_edges', []))}")
        return 0
    except Exception as exc:
        logger.exception("cmd_inspect_context: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)



def cmd_inspect_context_by_name(args: argparse.Namespace) -> int:
    """Inspect symbol context by qualified name.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    conn = get_connection_for_args(args)
    try:
        repo_id = args.repo_id
        qualified_name = args.qualified_name
        kind = getattr(args, "kind", None)

        if kind:
            symbol = get_symbol_by_qualified_name(conn, repo_id, qualified_name, kind=kind)
        else:
            symbol = get_symbol_by_qualified_name(conn, repo_id, qualified_name)

        if symbol is None:
            print(f"Symbol not found: {qualified_name}", file=sys.stderr)
            return 1

        symbol_id = symbol["id"]
        context = build_symbol_context(conn, symbol_id)
        data = _context_to_dict(context)

        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(f"\nContext: {data['focus_symbol']['qualified_name']}")
            print(f"  Kind: {data['focus_symbol']['kind']}")
        return 0
    except Exception as exc:
        logger.exception("cmd_inspect_context_by_name: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)



def cmd_inspect_references(args: argparse.Namespace) -> int:
    """Inspect stored incoming references for a symbol.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    conn = get_connection_for_args(args)
    try:
        symbol_id = args.symbol_id
        ref_edges = list_reference_edges_for_target(conn, symbol_id)
        ref_stats = build_reference_stats(conn, symbol_id)

        data = {
            "symbol_id": symbol_id,
            "reference_count": ref_stats.get("reference_count", 0),
            "referencing_files": ref_stats.get("referencing_file_count", 0),
            "referencing_modules": ref_stats.get("referencing_module_count", 0),
            "available": ref_stats.get("available", True),
            "references": [dict(r) if hasattr(r, "keys") else r for r in ref_edges],
        }

        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(f"\nSymbol: {symbol_id}")
            print(f"Reference count: {data['reference_count']}")
            print(f"Referencing files: {data['referencing_files']}")
            print(f"Referencing modules: {data['referencing_modules']}")
            print(f"Available: {data['available']}")
        return 0
    except Exception as exc:
        logger.exception("cmd_inspect_references: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)



def cmd_inspect_referenced_by(args: argparse.Namespace) -> int:
    """Inspect symbols that reference this symbol.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    conn = get_connection_for_args(args)
    try:
        symbol_id = args.symbol_id
        referenced_by = list_referenced_by(conn, symbol_id)

        data = {
            "symbol_id": symbol_id,
            "referenced_by": referenced_by,
        }

        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(f"\nSymbol: {symbol_id}")
            print(f"Referenced by ({len(referenced_by)} symbols):")
            for sym in referenced_by:
                print(f"  - {sym.get('qualified_name', sym.get('id', 'unknown'))} ({sym.get('kind', 'unknown')})")
        return 0
    except Exception as exc:
        logger.exception("cmd_inspect_referenced_by: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)



def cmd_inspect_references_from(args: argparse.Namespace) -> int:
    """Inspect outgoing reference edges from a symbol.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    conn = get_connection_for_args(args)
    try:
        symbol_id = args.symbol_id
        ref_edges = list_references_from_symbol(conn, symbol_id)

        data = {
            "symbol_id": symbol_id,
            "outgoing_references": [dict(r) if hasattr(r, "keys") else r for r in ref_edges],
        }

        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(f"\nSymbol: {symbol_id}")
            print(f"Outgoing references ({len(ref_edges)}):")
            for edge in ref_edges:
                print(f"  -> {edge.get('to_id', 'unknown')}")
        return 0
    except Exception as exc:
        logger.exception("cmd_inspect_references_from: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)



def cmd_inspect_risk(args: argparse.Namespace) -> int:
    """Inspect risk analysis for a symbol.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    conn = get_connection_for_args(args)
    try:
        symbol_id = args.symbol_id
        risk_result = analyze_symbol_risk(conn, symbol_id)
        data = _risk_to_dict(risk_result)

        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(f"\nRisk Analysis: {symbol_id}")
            print(f"Risk Score: {data['risk_score']}/100")
            print(f"Decision: {data['decision']}")
            print(f"Issues ({len(data['issues'])}):")
            for issue in data['issues']:
                print(f"  - {issue}")
        return 0
    except Exception as exc:
        logger.exception("cmd_inspect_risk: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)



def cmd_inspect_risk_set(args: argparse.Namespace) -> int:
    """Inspect risk analysis for multiple symbols.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    conn = get_connection_for_args(args)
    try:
        symbol_ids = args.symbol_ids
        risk_result = analyze_target_set_risk(conn, symbol_ids)
        data = _risk_to_dict(risk_result)

        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(f"\nRisk Analysis: {len(symbol_ids)} symbol(s)")
            print(f"Risk Score: {data['risk_score']}/100")
            print(f"Decision: {data['decision']}")
            print(f"Issues ({len(data['issues'])}):")
            for issue in data['issues']:
                print(f"  - {issue}")
        return 0
    except Exception as exc:
        logger.exception("cmd_inspect_risk_set: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)



def cmd_inspect_mcp_context(args: argparse.Namespace) -> int:
    """Inspect MCP-facing context payload.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    conn = get_connection_for_args(args)
    try:
        symbol_id = args.symbol_id
        context = build_symbol_context(conn, symbol_id)
        context_dict = _context_to_dict(context)
        mcp_payload = adapt_context(context_dict)
        data = {"ok": True, "data": {"context": mcp_payload}, "error": None}

        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(f"\nMCP Context payload for: {symbol_id}")
            print(f"  OK: {data['ok']}")
            print(f"  Context keys: {list(data['data']['context'].keys())}")  # type: ignore
        return 0
    except Exception as exc:
        logger.exception("cmd_inspect_mcp_context: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)



def cmd_inspect_mcp_references(args: argparse.Namespace) -> int:
    """Inspect MCP-facing references payload.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    conn = get_connection_for_args(args)
    try:
        symbol_id = args.symbol_id
        ref_edges = list_reference_edges_for_target(conn, symbol_id)
        ref_stats = build_reference_stats(conn, symbol_id)

        mcp_payload = adapt_references(ref_edges, ref_stats)
        data = {"ok": True, "data": mcp_payload, "error": None}

        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(f"\nMCP References payload for: {symbol_id}")
            print(f"  OK: {data['ok']}")
            print(f"  Reference count: {mcp_payload['reference_summary']['count']}")
        return 0
    except Exception as exc:
        logger.exception("cmd_inspect_mcp_references: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)



def cmd_inspect_mcp_risk(args: argparse.Namespace) -> int:
    """Inspect MCP-facing risk payload.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    conn = get_connection_for_args(args)
    try:
        symbol_id = args.symbol_id
        risk_result = analyze_symbol_risk(conn, symbol_id)
        risk_dict = _risk_to_dict(risk_result)
        mcp_payload = adapt_risk_result(risk_dict)
        data = {"ok": True, "data": {"risk": mcp_payload}, "error": None}

        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            print(f"\nMCP Risk payload for: {symbol_id}")
            print(f"  OK: {data['ok']}")
            print(f"  Risk score: {mcp_payload['risk_score']}")
            print(f"  Decision: {mcp_payload['decision']}")
        return 0
    except Exception as exc:
        logger.exception("cmd_inspect_mcp_risk: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)



def cmd_inspect_mcp_tool(args: argparse.Namespace) -> int:
    """Execute one MCP tool locally and print structured output.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """

    conn = get_connection_for_args(args)
    try:
        tool_name = args.tool_name
        tool_input = json.loads(args.json_input)

        handlers = {
            "resolve_symbol_tool": resolve_symbol,
            "get_symbol_context_tool": get_symbol_context,
            "get_symbol_references_tool": get_symbol_references,
            "analyze_symbol_risk_tool": mcp_analyze_symbol_risk,
        }

        if tool_name not in handlers:
            print(f"Unknown tool: {tool_name}. Available: {list(handlers.keys())}", file=sys.stderr)
            return 1

        handler: typing.Any = handlers[tool_name]
        result = asyncio.run(handler(conn, tool_input))

        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"\nMCP Tool: {tool_name}")
            print(f"  Input: {json.dumps(tool_input)}")
            print(f"  Result: {json.dumps(result, indent=2)}")
        return 0
    except json.JSONDecodeError as exc:
        logger.exception("cmd_inspect_mcp_tool: Invalid JSON input")
        print(f"Error: Invalid JSON input: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.exception("cmd_inspect_mcp_tool: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)
