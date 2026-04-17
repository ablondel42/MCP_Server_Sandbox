"""CLI main entry point."""

import argparse
import sys
from pathlib import Path

from repo_context.logging_config import get_logger




from .commands.run import cmd_run, cmd_scan_repo, cmd_extract_ast
from .commands.inspect import cmd_inspect_file, cmd_inspect_node, cmd_inspect_edge, cmd_inspect_graph_for_file, cmd_inspect_context, cmd_inspect_context_by_name, cmd_inspect_references, cmd_inspect_referenced_by, cmd_inspect_references_from, cmd_inspect_risk, cmd_inspect_risk_set, cmd_inspect_mcp_context, cmd_inspect_mcp_references, cmd_inspect_mcp_risk, cmd_inspect_mcp_tool
from .commands.query import cmd_symbol_context, cmd_symbol_references, cmd_refresh_references, cmd_show_references, cmd_show_referenced_by, cmd_list_nodes, cmd_show_node, cmd_find_symbol
from .commands.maintenance import cmd_init_db, cmd_doctor, cmd_graph_stats
from .commands.risk import cmd_risk_symbol, cmd_risk_targets
from .commands.validation import cmd_validate_workflow, cmd_validate_symbol_workflow
from .commands.debug import cmd_debug_reindex_file, cmd_debug_delete_file, cmd_debug_normalize_event
from .commands.server import cmd_serve_mcp, cmd_watch










































# ==================== Inspection Commands ====================










































# ==================== Helper Functions ====================




















logger = get_logger("cli.main")


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        prog="repo-context",
        description="Repository intelligence for safer AI-assisted code planning",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init-db command
    init_parser = subparsers.add_parser("init-db", help="Initialize database")
    init_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    init_parser.set_defaults(func=cmd_init_db)

    # doctor command
    doctor_parser = subparsers.add_parser("doctor", help="Health check")
    doctor_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    doctor_parser.set_defaults(func=cmd_doctor)

    # run command (with subcommands)
    # Arguments are defined on parent so they work with or without subcommand
    run_parser = subparsers.add_parser("run", help="Setup and scan for testing")
    run_parser.add_argument(
        "run_command",
        type=str,
        nargs="?",
        default="full",
        choices=["full", "init-db", "scan"],
        help="Run subcommand (default: full)",
    )
    run_parser.add_argument(
        "repo_path",
        type=Path,
        nargs="?",
        default=None,
        help="Path to the repository to scan (default: current working directory)",
    )
    run_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    run_parser.add_argument(
        "--json",
        action="store_true",
        help="Output summary as JSON",
    )
    run_parser.set_defaults(func=cmd_run)

    # scan-repo command
    scan_parser = subparsers.add_parser("scan-repo", help="Scan a repository")
    scan_parser.add_argument(
        "repo_path",
        type=Path,
        help="Path to the repository to scan",
    )
    scan_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    scan_parser.add_argument(
        "--json",
        action="store_true",
        help="Output summary as JSON",
    )
    scan_parser.set_defaults(func=cmd_scan_repo)

    # extract-ast command
    extract_parser = subparsers.add_parser("extract-ast", help="Extract AST from scanned repository")
    extract_parser.add_argument(
        "repo_path",
        type=Path,
        help="Path to the repository to process",
    )
    extract_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    extract_parser.add_argument(
        "--json",
        action="store_true",
        help="Output summary as JSON",
    )
    extract_parser.set_defaults(func=cmd_extract_ast)

    # graph-stats command
    stats_parser = subparsers.add_parser("graph-stats", help="Show graph statistics")
    stats_parser.add_argument(
        "repo_id",
        type=str,
        help="Repository ID",
    )
    stats_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    stats_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    stats_parser.set_defaults(func=cmd_graph_stats)

    # find-symbol command
    find_parser = subparsers.add_parser("find-symbol", help="Find symbols by name or qualified name pattern")
    find_parser.add_argument(
        "repo_id",
        type=str,
        help="Repository ID",
    )
    find_parser.add_argument(
        "pattern",
        type=str,
        help="Name or qualified name pattern (supports %% wildcard)",
    )
    find_parser.add_argument(
        "--kind",
        type=str,
        choices=["module", "class", "function", "async_function", "method", "async_method", "local_function", "local_async_function"],
        help="Filter by symbol kind",
    )
    find_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of results (default: 50)",
    )
    find_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    find_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    find_parser.set_defaults(func=cmd_find_symbol)

    # symbol-context command
    context_parser = subparsers.add_parser("symbol-context", help="Get full context for a symbol including relationships")
    context_parser.add_argument(
        "repo_id",
        type=str,
        help="Repository ID",
    )
    context_parser.add_argument(
        "identifier",
        type=str,
        help="Node ID or symbol name",
    )
    context_parser.add_argument(
        "--by-name",
        action="store_true",
        help="Search by name pattern instead of exact ID",
    )
    context_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    context_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    context_parser.set_defaults(func=cmd_symbol_context)

    # symbol-references command
    refs_parser = subparsers.add_parser("symbol-references", help="Get incoming/outgoing references for a symbol")
    refs_parser.add_argument(
        "repo_id",
        type=str,
        help="Repository ID",
    )
    refs_parser.add_argument(
        "identifier",
        type=str,
        help="Node ID or symbol name",
    )
    refs_parser.add_argument(
        "--by-name",
        action="store_true",
        help="Search by name pattern instead of exact ID",
    )
    refs_parser.add_argument(
        "--direction",
        type=str,
        choices=["incoming", "outgoing", "both"],
        default="both",
        help="Which edges to show (default: both)",
    )
    refs_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    refs_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    refs_parser.set_defaults(func=cmd_symbol_references)

    # list-nodes command
    list_parser = subparsers.add_parser("list-nodes", help="List nodes for a repository")
    list_parser.add_argument(
        "repo_id",
        type=str,
        help="Repository ID",
    )
    list_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    list_parser.set_defaults(func=cmd_list_nodes)

    # show-node command
    show_parser = subparsers.add_parser("show-node", help="Show details for a specific node")
    show_parser.add_argument(
        "node_id",
        type=str,
        help="Node ID",
    )
    show_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    show_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    show_parser.set_defaults(func=cmd_show_node)

    # refresh-references command
    refresh_parser = subparsers.add_parser("refresh-references", help="Refresh LSP references for a symbol")
    refresh_parser.add_argument(
        "node_id",
        type=str,
        help="Symbol ID to refresh",
    )
    refresh_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    refresh_parser.set_defaults(func=cmd_refresh_references)

    # show-references command
    show_refs_parser = subparsers.add_parser("show-references", help="Show stored incoming references for a symbol")
    show_refs_parser.add_argument(
        "node_id",
        type=str,
        help="Symbol ID",
    )
    show_refs_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    show_refs_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    show_refs_parser.set_defaults(func=cmd_show_references)

    # show-referenced-by command
    show_refby_parser = subparsers.add_parser("show-referenced-by", help="Show symbols that reference this symbol")
    show_refby_parser.add_argument(
        "node_id",
        type=str,
        help="Symbol ID",
    )
    show_refby_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    show_refby_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    show_refby_parser.set_defaults(func=cmd_show_referenced_by)

    # risk-symbol command
    risk_symbol_parser = subparsers.add_parser("risk-symbol", help="Analyze risk for a single symbol")
    risk_symbol_parser.add_argument(
        "symbol_id",
        type=str,
        help="Symbol ID to analyze",
    )
    risk_symbol_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    risk_symbol_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    risk_symbol_parser.set_defaults(func=cmd_risk_symbol)

    # risk-targets command
    risk_targets_parser = subparsers.add_parser("risk-targets", help="Analyze risk for multiple symbols")
    risk_targets_parser.add_argument(
        "symbol_ids",
        type=str,
        nargs="+",
        help="Symbol IDs to analyze",
    )
    risk_targets_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    risk_targets_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    risk_targets_parser.set_defaults(func=cmd_risk_targets)

    # serve-mcp command
    serve_mcp_parser = subparsers.add_parser("serve-mcp", help="Start MCP server on stdio")
    serve_mcp_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    serve_mcp_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    serve_mcp_parser.set_defaults(func=cmd_serve_mcp)

    # watch command
    watch_parser = subparsers.add_parser("watch", help="Watch repository for file changes")
    watch_parser.add_argument(
        "repo_root",
        type=Path,
        help="Path to repository root",
    )
    watch_parser.add_argument(
        "--debounce-ms",
        type=int,
        default=500,
        help="Debounce window in milliseconds (default: 500)",
    )
    watch_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    watch_parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: repo_context.db)",
    )
    watch_parser.set_defaults(func=cmd_watch)

    # ==================== Inspection Commands ====================

    # inspect-file
    inspect_file_parser = subparsers.add_parser("inspect-file", help="Inspect tracked file metadata")
    inspect_file_parser.add_argument("repo_id", type=str, help="Repository ID")
    inspect_file_parser.add_argument("file_path", type=str, help="Repository-relative file path")
    inspect_file_parser.add_argument("--db-path", type=Path, help="Path to database file")
    inspect_file_parser.add_argument("--json", action="store_true", help="Output as JSON")
    inspect_file_parser.set_defaults(func=cmd_inspect_file)

    # inspect-node
    inspect_node_parser = subparsers.add_parser("inspect-node", help="Inspect a stored node payload")
    inspect_node_parser.add_argument("node_id", type=str, help="Node ID")
    inspect_node_parser.add_argument("--db-path", type=Path, help="Path to database file")
    inspect_node_parser.add_argument("--json", action="store_true", help="Output as JSON")
    inspect_node_parser.set_defaults(func=cmd_inspect_node)

    # inspect-edge
    inspect_edge_parser = subparsers.add_parser("inspect-edge", help="Inspect a stored edge payload")
    inspect_edge_parser.add_argument("edge_id", type=str, help="Edge ID")
    inspect_edge_parser.add_argument("--db-path", type=Path, help="Path to database file")
    inspect_edge_parser.add_argument("--json", action="store_true", help="Output as JSON")
    inspect_edge_parser.set_defaults(func=cmd_inspect_edge)

    # inspect-graph-for-file
    inspect_graph_parser = subparsers.add_parser("inspect-graph-for-file", help="List nodes and edges owned by one file")
    inspect_graph_parser.add_argument("file_path", type=str, help="Repository-relative file path")
    inspect_graph_parser.add_argument("--db-path", type=Path, help="Path to database file")
    inspect_graph_parser.add_argument("--json", action="store_true", help="Output as JSON")
    inspect_graph_parser.add_argument("--kinds", nargs="+", help="Filter by node kinds")
    inspect_graph_parser.set_defaults(func=cmd_inspect_graph_for_file)

    # inspect-context
    inspect_context_parser = subparsers.add_parser("inspect-context", help="Inspect symbol context")
    inspect_context_parser.add_argument("symbol_id", type=str, help="Symbol ID")
    inspect_context_parser.add_argument("--db-path", type=Path, help="Path to database file")
    inspect_context_parser.add_argument("--json", action="store_true", help="Output as JSON")
    inspect_context_parser.set_defaults(func=cmd_inspect_context)

    # inspect-context-by-name
    inspect_context_by_name_parser = subparsers.add_parser("inspect-context-by-name", help="Inspect symbol context by qualified name")
    inspect_context_by_name_parser.add_argument("repo_id", type=str, help="Repository ID")
    inspect_context_by_name_parser.add_argument("qualified_name", type=str, help="Qualified name")
    inspect_context_by_name_parser.add_argument("--kind", type=str, help="Symbol kind filter")
    inspect_context_by_name_parser.add_argument("--db-path", type=Path, help="Path to database file")
    inspect_context_by_name_parser.add_argument("--json", action="store_true", help="Output as JSON")
    inspect_context_by_name_parser.set_defaults(func=cmd_inspect_context_by_name)

    # inspect-references
    inspect_refs_parser = subparsers.add_parser("inspect-references", help="Inspect stored incoming references")
    inspect_refs_parser.add_argument("symbol_id", type=str, help="Symbol ID")
    inspect_refs_parser.add_argument("--db-path", type=Path, help="Path to database file")
    inspect_refs_parser.add_argument("--json", action="store_true", help="Output as JSON")
    inspect_refs_parser.set_defaults(func=cmd_inspect_references)

    # inspect-referenced-by
    inspect_refby_parser = subparsers.add_parser("inspect-referenced-by", help="Inspect symbols that reference this symbol")
    inspect_refby_parser.add_argument("symbol_id", type=str, help="Symbol ID")
    inspect_refby_parser.add_argument("--db-path", type=Path, help="Path to database file")
    inspect_refby_parser.add_argument("--json", action="store_true", help="Output as JSON")
    inspect_refby_parser.set_defaults(func=cmd_inspect_referenced_by)

    # inspect-references-from
    inspect_refs_from_parser = subparsers.add_parser("inspect-references-from", help="Inspect outgoing reference edges")
    inspect_refs_from_parser.add_argument("symbol_id", type=str, help="Symbol ID")
    inspect_refs_from_parser.add_argument("--db-path", type=Path, help="Path to database file")
    inspect_refs_from_parser.add_argument("--json", action="store_true", help="Output as JSON")
    inspect_refs_from_parser.set_defaults(func=cmd_inspect_references_from)

    # inspect-risk
    inspect_risk_parser = subparsers.add_parser("inspect-risk", help="Inspect risk analysis for a symbol")
    inspect_risk_parser.add_argument("symbol_id", type=str, help="Symbol ID")
    inspect_risk_parser.add_argument("--db-path", type=Path, help="Path to database file")
    inspect_risk_parser.add_argument("--json", action="store_true", help="Output as JSON")
    inspect_risk_parser.set_defaults(func=cmd_inspect_risk)

    # inspect-risk-set
    inspect_risk_set_parser = subparsers.add_parser("inspect-risk-set", help="Inspect risk analysis for multiple symbols")
    inspect_risk_set_parser.add_argument("symbol_ids", type=str, nargs="+", help="Symbol IDs to analyze")
    inspect_risk_set_parser.add_argument("--db-path", type=Path, help="Path to database file")
    inspect_risk_set_parser.add_argument("--json", action="store_true", help="Output as JSON")
    inspect_risk_set_parser.set_defaults(func=cmd_inspect_risk_set)

    # inspect-mcp-context
    inspect_mcp_ctx_parser = subparsers.add_parser("inspect-mcp-context", help="Inspect MCP-facing context payload")
    inspect_mcp_ctx_parser.add_argument("symbol_id", type=str, help="Symbol ID")
    inspect_mcp_ctx_parser.add_argument("--db-path", type=Path, help="Path to database file")
    inspect_mcp_ctx_parser.add_argument("--json", action="store_true", help="Output as JSON")
    inspect_mcp_ctx_parser.set_defaults(func=cmd_inspect_mcp_context)

    # inspect-mcp-references
    inspect_mcp_refs_parser = subparsers.add_parser("inspect-mcp-references", help="Inspect MCP-facing references payload")
    inspect_mcp_refs_parser.add_argument("symbol_id", type=str, help="Symbol ID")
    inspect_mcp_refs_parser.add_argument("--db-path", type=Path, help="Path to database file")
    inspect_mcp_refs_parser.add_argument("--json", action="store_true", help="Output as JSON")
    inspect_mcp_refs_parser.set_defaults(func=cmd_inspect_mcp_references)

    # inspect-mcp-risk
    inspect_mcp_risk_parser = subparsers.add_parser("inspect-mcp-risk", help="Inspect MCP-facing risk payload")
    inspect_mcp_risk_parser.add_argument("symbol_id", type=str, help="Symbol ID")
    inspect_mcp_risk_parser.add_argument("--db-path", type=Path, help="Path to database file")
    inspect_mcp_risk_parser.add_argument("--json", action="store_true", help="Output as JSON")
    inspect_mcp_risk_parser.set_defaults(func=cmd_inspect_mcp_risk)

    # inspect-mcp-tool
    inspect_mcp_tool_parser = subparsers.add_parser("inspect-mcp-tool", help="Execute one MCP tool locally")
    inspect_mcp_tool_parser.add_argument("tool_name", type=str, help="MCP tool name")
    inspect_mcp_tool_parser.add_argument("json_input", type=str, help="JSON input for the tool")
    inspect_mcp_tool_parser.add_argument("--db-path", type=Path, help="Path to database file")
    inspect_mcp_tool_parser.add_argument("--json", action="store_true", help="Output as JSON")
    inspect_mcp_tool_parser.set_defaults(func=cmd_inspect_mcp_tool)

    # validate-workflow
    validate_wf_parser = subparsers.add_parser("validate-workflow", help="Run full workflow validation")
    validate_wf_parser.add_argument("repo_root", type=Path, help="Path to repository root")
    validate_wf_parser.add_argument("--fixture-name", type=str, help="Fixture name for report")
    validate_wf_parser.add_argument("--db-path", type=Path, help="Path to database file")
    validate_wf_parser.add_argument("--json", action="store_true", help="Output as JSON")
    validate_wf_parser.set_defaults(func=cmd_validate_workflow)

    # validate-symbol-workflow
    validate_sym_wf_parser = subparsers.add_parser("validate-symbol-workflow", help="Run symbol workflow validation")
    validate_sym_wf_parser.add_argument("symbol_id", type=str, help="Symbol ID")
    validate_sym_wf_parser.add_argument("--db-path", type=Path, help="Path to database file")
    validate_sym_wf_parser.add_argument("--json", action="store_true", help="Output as JSON")
    validate_sym_wf_parser.set_defaults(func=cmd_validate_symbol_workflow)

    # debug-reindex-file
    debug_reindex_parser = subparsers.add_parser("debug-reindex-file", help="Run incremental reindex for a file")
    debug_reindex_parser.add_argument("repo_root", type=Path, help="Path to repository root")
    debug_reindex_parser.add_argument("file_path", type=str, help="File path (relative to repo_root)")
    debug_reindex_parser.add_argument("--db-path", type=Path, help="Path to database file")
    debug_reindex_parser.add_argument("--json", action="store_true", help="Output as JSON")
    debug_reindex_parser.set_defaults(func=cmd_debug_reindex_file)

    # debug-delete-file
    debug_delete_parser = subparsers.add_parser("debug-delete-file", help="Run deleted-file cleanup for a file")
    debug_delete_parser.add_argument("repo_id", type=str, help="Repository ID")
    debug_delete_parser.add_argument("file_path", type=str, help="Repository-relative file path")
    debug_delete_parser.add_argument("--db-path", type=Path, help="Path to database file")
    debug_delete_parser.add_argument("--json", action="store_true", help="Output as JSON")
    debug_delete_parser.set_defaults(func=cmd_debug_delete_file)

    # debug-normalize-event
    debug_event_parser = subparsers.add_parser("debug-normalize-event", help="Run event normalization")
    debug_event_parser.add_argument("repo_root", type=Path, help="Path to repository root")
    debug_event_parser.add_argument("file_path", type=str, help="File path")
    debug_event_parser.add_argument("--event-type", type=str, required=True, choices=["created", "modified", "deleted"])
    debug_event_parser.add_argument("--json", action="store_true", help="Output as JSON")
    debug_event_parser.set_defaults(func=cmd_debug_normalize_event)

    args = parser.parse_args()
    
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        logger.exception("CLI: File or directory not found")
        print(f"Error: File or directory not found: {exc}", file=sys.stderr)
        return 1
    except NotADirectoryError as exc:
        logger.exception("CLI: Path is not a directory")
        print(f"Error: Not a directory: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.exception("CLI: Command failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
