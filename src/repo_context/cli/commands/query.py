"""CLI main entry point."""

import argparse
import json
import sys

from repo_context.config import get_config
from repo_context.logging_config import get_logger
from repo_context.storage import (
    get_connection,
    close_connection,
    list_nodes_for_repo,
    get_node_by_id,
    get_node_by_qualified_name,
)
from repo_context.graph import (
    find_symbols_by_name,
    build_reference_stats,
    list_reference_edges_for_target,
    list_referenced_by,
)
from repo_context.context import build_symbol_context
from repo_context.lsp import PyrightLspClient
from repo_context.lsp.references import enrich_references_for_symbol
from repo_context.storage.files import get_file_by_id
from pathlib import Path

logger = get_logger("cli.main")





def cmd_symbol_context(args: argparse.Namespace) -> int:
    """Get full context for a symbol including relationships and references.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    repo_id = args.repo_id
    identifier = args.identifier

    try:
        conn = get_connection(db_path)
        try:
            # Find the symbol
            if args.by_name:
                symbol = _find_symbol_by_name_or_id(conn, repo_id, identifier)
                if symbol is None:
                    print(f"Error: Symbol '{identifier}' not found or ambiguous", file=sys.stderr)
                    return 1
                node_id = symbol["id"]
            else:
                node_id = identifier

            # Build context
            context = build_symbol_context(conn, node_id)
            if context is None:
                print(f"Error: Symbol not found: {node_id}", file=sys.stderr)
                return 1

            if args.json:
                # Serialize context to JSON
                output = {
                    "focus_symbol": context.focus_symbol,
                    "structural_parent": context.structural_parent,
                    "structural_children": context.structural_children,
                    "lexical_parent": context.lexical_parent,
                    "lexical_children": context.lexical_children,
                    "incoming_edges": context.incoming_edges,
                    "outgoing_edges": context.outgoing_edges,
                    "file_siblings": context.file_siblings,
                    "structural_summary": context.structural_summary,
                    "freshness": context.freshness,
                    "confidence": context.confidence,
                }
                print(json.dumps(output, indent=2))
            else:
                # Print human-readable format
                focus = context.focus_symbol
                print(f"\nSymbol Context: {focus['qualified_name']}")
                print("=" * 60)

                print("\nFocus Symbol:")
                print(f"  Kind: {focus['kind']}")
                print(f"  File: {focus['file_id']}")
                print(f"  Scope: {focus['scope']}")

                print("\nStructural Relationships:")
                if context.structural_parent:
                    print(f"  Parent: {context.structural_parent['qualified_name']} ({context.structural_parent['kind']})")
                else:
                    print("  Parent: None")
                
                if context.structural_children:
                    print(f"  Children ({len(context.structural_children)}):")
                    for child in context.structural_children[:10]:
                        print(f"    - {child['name']} ({child['kind']})")
                    if len(context.structural_children) > 10:
                        print(f"    ... and {len(context.structural_children) - 10} more")
                else:
                    print("  Children: None")

                print("\nLexical Relationships:")
                if context.lexical_parent:
                    print(f"  Parent: {context.lexical_parent['qualified_name']} ({context.lexical_parent['kind']})")
                else:
                    print("  Parent: None")
                
                if context.lexical_children:
                    print(f"  Children ({len(context.lexical_children)}):")
                    for child in context.lexical_children[:10]:
                        print(f"    - {child['name']} ({child['kind']})")
                    if len(context.lexical_children) > 10:
                        print(f"    ... and {len(context.lexical_children) - 10} more")
                else:
                    print("  Children: None")

                print(f"\nIncoming Edges ({len(context.incoming_edges)}):")
                if context.incoming_edges:
                    for edge in context.incoming_edges[:10]:
                        print(f"  [{edge['kind']}] {edge['from_id']} -> {edge['to_id']}")
                    if len(context.incoming_edges) > 10:
                        print(f"  ... and {len(context.incoming_edges) - 10} more")
                else:
                    print("  (none)")

                print(f"\nOutgoing Edges ({len(context.outgoing_edges)}):")
                if context.outgoing_edges:
                    for edge in context.outgoing_edges[:10]:
                        print(f"  [{edge['kind']}] {edge['from_id']} -> {edge['to_id']}")
                    if len(context.outgoing_edges) > 10:
                        print(f"  ... and {len(context.outgoing_edges) - 10} more")
                else:
                    print("  (none)")

                print(f"\nFile Siblings ({len(context.file_siblings)}):")
                if context.file_siblings:
                    for sib in context.file_siblings[:10]:
                        print(f"  - {sib['name']} ({sib['kind']})")
                    if len(context.file_siblings) > 10:
                        print(f"  ... and {len(context.file_siblings) - 10} more")
                else:
                    print("  (none)")

                print("\nSummary:")
                summary = context.structural_summary
                print(f"  - Has structural parent: {'Yes' if summary['has_structural_parent'] else 'No'}")
                print(f"  - Structural children: {summary['structural_child_count']}")
                print(f"  - Has lexical parent: {'Yes' if summary['has_lexical_parent'] else 'No'}")
                print(f"  - Lexical children: {summary['lexical_child_count']}")
                print(f"  - Incoming edges: {summary['incoming_edge_count']}")
                print(f"  - Outgoing edges: {summary['outgoing_edge_count']}")
                print(f"  - Is local declaration: {'Yes' if summary['is_local_declaration'] else 'No'}")

            return 0
        finally:
            close_connection(conn)
    except Exception as exc:
        print(f"Error getting symbol context: {exc}", file=sys.stderr)
        return 1



def cmd_symbol_references(args: argparse.Namespace) -> int:
    """Get incoming and/or outgoing references (edges) for a symbol.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    repo_id = args.repo_id
    identifier = args.identifier
    direction = args.direction

    try:
        conn = get_connection(db_path)
        try:
            # Find the symbol
            if args.by_name:
                symbol = _find_symbol_by_name_or_id(conn, repo_id, identifier)
                if symbol is None:
                    print(f"Error: Symbol '{identifier}' not found or ambiguous", file=sys.stderr)
                    return 1
                node_id = symbol["id"]
            else:
                node_id = identifier
                symbol = get_node_by_id(conn, node_id)
                if symbol is None:
                    print(f"Error: Symbol not found: {node_id}", file=sys.stderr)
                    return 1

            # Get edges from context
            context = build_symbol_context(conn, node_id)
            if context is None:
                print(f"Error: Could not build context for: {node_id}", file=sys.stderr)
                return 1

            # Handle both Pydantic model and dict
            if isinstance(context, dict):
                incoming_edges = context.get("incoming_edges", [])
                outgoing_edges = context.get("outgoing_edges", [])
            else:
                incoming_edges = context.incoming_edges
                outgoing_edges = context.outgoing_edges

            # Filter edges by direction
            edges_to_show = []
            if direction in ("incoming", "both"):
                edges_to_show.append(("incoming", incoming_edges))
            if direction in ("outgoing", "both"):
                edges_to_show.append(("outgoing", outgoing_edges))

            if args.json:
                output = {
                    "symbol": symbol,
                    "edges": {},
                }
                for edge_type, edge_list in edges_to_show:
                    output["edges"][edge_type] = edge_list
                print(json.dumps(output, indent=2))
            else:
                print(f"\nReferences for: {symbol['qualified_name']}")
                print("=" * 60)

                for edge_type, edge_list in edges_to_show:
                    print(f"\n{edge_type.title()} Edges ({len(edge_list)}):")
                    if edge_list:
                        for edge in edge_list[:20]:
                            if edge_type == "incoming":
                                print(f"  [{edge['kind']}] {edge['from_id']} -> {edge['to_id']}")
                            else:
                                print(f"  [{edge['kind']}] {edge['from_id']} -> {edge['to_id']}")
                        if len(edge_list) > 20:
                            print(f"  ... and {len(edge_list) - 20} more")
                    else:
                        print("  (none)")

            return 0
        finally:
            close_connection(conn)
    except Exception as exc:
        print(f"Error getting symbol references: {exc}", file=sys.stderr)
        return 1



def cmd_refresh_references(args: argparse.Namespace) -> int:
    """Refresh LSP references for a symbol.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    logger = get_logger("cli.refresh_references")
    
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    node_id = args.node_id

    try:
        conn = get_connection(db_path)
        try:
            # Find the symbol
            symbol = get_node_by_id(conn, node_id)
            if symbol is None:
                logger.error(f"Symbol not found: {node_id}")
                return 1

            # Get file record to find repo root
            file_record = get_file_by_id(conn, symbol["file_id"])
            if file_record is None:
                logger.error(f"File not found for symbol: {symbol['file_id']}")
                return 1

            # Get repo root
            repo_root = str(Path.cwd())  # Use current working directory as repo root

            # Enrich references - build proper symbol dict with required fields
            target_symbol = {
                "id": symbol["id"],
                "repo_id": symbol["repo_id"],
                "file_id": symbol["file_id"],
                "file_path": file_record["file_path"],
                "uri": symbol["uri"],
                "qualified_name": symbol["qualified_name"],
                "kind": symbol["kind"],
                "scope": symbol.get("scope"),
                "range_json": symbol.get("range_json"),
                "selection_range_json": symbol.get("selection_range_json"),
                "repo_root": repo_root,
            }

            with PyrightLspClient() as client:
                stats = enrich_references_for_symbol(conn, client, target_symbol, open_all_files=True)

            logger.info(f"References refreshed for: {symbol['qualified_name']}")
            logger.info(f"  Reference count: {stats['reference_count']}")
            logger.info(f"  Referencing files: {stats['referencing_file_count']}")
            logger.info(f"  Referencing modules: {stats['referencing_module_count']}")
            logger.info(f"  Available: {stats['available']}")
            logger.info(f"  Last refreshed: {stats['last_refreshed_at']}")

            return 0
        finally:
            close_connection(conn)
    except Exception as exc:
        logger.exception(f"Error refreshing references: {exc}")
        return 1



def cmd_show_references(args: argparse.Namespace) -> int:
    """Show stored incoming references for a symbol.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    node_id = args.node_id

    try:
        conn = get_connection(db_path)
        try:
            # Get symbol
            symbol = get_node_by_id(conn, node_id)
            if symbol is None:
                print(f"Error: Symbol not found: {node_id}", file=sys.stderr)
                return 1

            # Get reference stats
            stats = build_reference_stats(conn, node_id)

            if args.json:
                output = {
                    "symbol": symbol,
                    "stats": stats,
                }
                print(json.dumps(output, indent=2))
            else:
                print(f"Symbol: {symbol['qualified_name']}")
                print(f"Reference count: {stats['reference_count']}")
                print(f"Referencing files: {stats['referencing_file_count']}")
                print(f"Referencing modules: {stats['referencing_module_count']}")
                print(f"Available: {stats['available']}")
                print(f"Last refreshed: {stats['last_refreshed_at']}")

                if stats["available"]:
                    edges = list_reference_edges_for_target(conn, node_id)
                    if edges:
                        print(f"\nReferences ({len(edges)}):")
                        for edge in edges[:10]:
                            range_data = edge['evidence_range_json']
                            if isinstance(range_data, str):
                                range_data = json.loads(range_data)
                            line = range_data['start']['line']
                            print(f"  <- {edge['from_id']} at {edge['evidence_uri']}:{line}")
                        if len(edges) > 10:
                            print(f"  ... and {len(edges) - 10} more")
                    else:
                        print("\n  (no references found)")

            return 0
        finally:
            close_connection(conn)
    except Exception as exc:
        print(f"Error showing references: {exc}", file=sys.stderr)
        return 1



def cmd_show_referenced_by(args: argparse.Namespace) -> int:
    """Show symbols that reference this symbol (reverse lookup).

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    node_id = args.node_id

    try:
        conn = get_connection(db_path)
        try:
            # Get symbol
            symbol = get_node_by_id(conn, node_id)
            if symbol is None:
                print(f"Error: Symbol not found: {node_id}", file=sys.stderr)
                return 1

            # Get reverse references
            referenced_by = list_referenced_by(conn, node_id)

            if args.json:
                output = {
                    "symbol": symbol,
                    "referenced_by": referenced_by,
                }
                print(json.dumps(output, indent=2))
            else:
                print(f"Symbol: {symbol['qualified_name']}")
                print(f"Referenced by ({len(referenced_by)} symbols):")
                if referenced_by:
                    for ref in referenced_by[:10]:
                        print(f"  - {ref['qualified_name']} ({ref['kind']})")
                    if len(referenced_by) > 10:
                        print(f"  ... and {len(referenced_by) - 10} more")
                else:
                    print("  (none)")

            return 0
        finally:
            close_connection(conn)
    except Exception as exc:
        print(f"Error showing referenced-by: {exc}", file=sys.stderr)
        return 1



def cmd_list_nodes(args: argparse.Namespace) -> int:
    """List nodes for a repository.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    repo_id = args.repo_id

    try:
        conn = get_connection(db_path)
        try:
            nodes = list_nodes_for_repo(conn, repo_id)
            
            if args.json:
                print(json.dumps(nodes, indent=2))
            else:
                print(f"Nodes in {repo_id}:")
                for node in nodes:
                    print(f"  [{node['kind']}] {node['qualified_name']}")
            
            return 0
        finally:
            close_connection(conn)
    except Exception as exc:
        print(f"Error listing nodes: {exc}", file=sys.stderr)
        return 1



def cmd_show_node(args: argparse.Namespace) -> int:
    """Show details for a specific node.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    node_id = args.node_id

    try:
        conn = get_connection(db_path)
        try:
            node = get_node_by_id(conn, node_id)

            if node is None:
                logger.error("Node not found", extra={"node_id": node_id})
                print(f"Error: Node not found: {node_id}", file=sys.stderr)
                return 1

            logger.info("Node details retrieved", extra={"node_id": node_id})

            if args.json:
                print(json.dumps(node, indent=2))
            else:
                print(f"Node: {node['id']}")
                print(f"  Kind: {node['kind']}")
                print(f"  Name: {node['name']}")
                print(f"  Qualified Name: {node['qualified_name']}")
                print(f"  File: {node['file_id']}")
                print(f"  Scope: {node.get('scope', 'N/A')}")
                print(f"  Parent ID: {node.get('parent_id', 'N/A')}")
                print(f"  Lexical Parent ID: {node.get('lexical_parent_id', 'N/A')}")

            return 0
        finally:
            close_connection(conn)
    except Exception:
        logger.exception("cmd_show_node: Failed to show node")
        raise



def cmd_find_symbol(args: argparse.Namespace) -> int:
    """Find symbols by name or qualified name pattern.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    repo_id = args.repo_id
    pattern = args.pattern

    try:
        conn = get_connection(db_path)
        try:
            # Convert simple pattern to wildcard pattern if no % provided
            if "%" not in pattern:
                pattern = f"%{pattern}%"

            symbols = find_symbols_by_name(
                conn, repo_id, pattern,
                kind=args.kind,
                limit=args.limit
            )

            if args.json:
                print(json.dumps(symbols, indent=2))
            else:
                print(f"Symbols matching '{pattern}' in {repo_id}:")
                if not symbols:
                    print("  (no matches)")
                else:
                    for symbol in symbols:
                        print(f"  [{symbol['kind']}] {symbol['qualified_name']}")
                print(f"\nFound {len(symbols)} symbol(s)")

            return 0
        finally:
            close_connection(conn)
    except Exception as exc:
        print(f"Error finding symbols: {exc}", file=sys.stderr)
        return 1



def _find_symbol_by_name_or_id(
    conn,
    repo_id: str,
    identifier: str,
) -> dict | None:
    """Find a symbol by ID or by name pattern.
    
    Args:
        conn: SQLite connection.
        repo_id: Repository ID.
        identifier: Either a full node ID or a name pattern.
        
    Returns:
        Symbol dictionary or None if not found or ambiguous.
    """
    # Try as exact ID first
    if identifier.startswith("sym:"):
        return get_node_by_id(conn, identifier)
    
    # Try as exact qualified name
    symbol = get_node_by_qualified_name(conn, repo_id, identifier)
    if symbol is not None:
        return symbol
    
    # Try as exact name match (not pattern)
    symbols = find_symbols_by_name(conn, repo_id, identifier, limit=10)
    # Look for exact name match first
    for sym in symbols:
        if sym["name"] == identifier:
            return sym
    
    # If no exact match, check if there's only one result
    if len(symbols) == 1:
        return symbols[0]
    
    # Multiple matches - return None (ambiguous)
    return None
