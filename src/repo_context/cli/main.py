"""CLI main entry point."""

import argparse
import json
import sys
from pathlib import Path

from repo_context.config import get_config
from repo_context.storage import (
    get_connection,
    close_connection,
    initialize_database,
    upsert_repo,
    upsert_files,
    upsert_nodes,
    upsert_edges,
    list_files_for_repo,
    get_repo_by_id,
    list_nodes_for_repo,
    list_edges_for_repo,
    get_node_by_id,
)
from repo_context.graph import get_repo_graph_stats
from repo_context.parsing.scanner import scan_repository
from repo_context.parsing.pipeline import extract_file_graph


def cmd_init_db(args: argparse.Namespace) -> int:
    """Initialize the database.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path

    try:
        conn = get_connection(db_path)
        initialize_database(conn)
        close_connection(conn)
        print(f"Database initialized at {db_path}")
        return 0
    except Exception as exc:
        print(f"Error initializing database: {exc}", file=sys.stderr)
        return 1


def cmd_doctor(args: argparse.Namespace) -> int:
    """Run health checks.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path

    errors = []

    # Check config
    print(f"Config: app_name={config.app_name}, debug={config.debug}")

    # Check database connection and schema
    try:
        conn = get_connection(db_path)
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}
        expected_tables = {"repos", "files", "nodes", "edges", "index_runs"}
        missing_tables = expected_tables - tables
        if missing_tables:
            errors.append(f"Missing tables: {missing_tables}")
        else:
            print(f"Tables: OK ({len(tables)} tables)")

        # Check indexes exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        expected_indexes = {
            "idx_nodes_repo_id",
            "idx_nodes_file_id",
            "idx_nodes_qualified_name",
            "idx_nodes_parent_id",
            "idx_nodes_kind",
            "idx_edges_repo_id",
            "idx_edges_from_id",
            "idx_edges_to_id",
            "idx_edges_kind",
            "idx_edges_evidence_file_id",
            "idx_files_repo_id",
            "idx_index_runs_repo_id",
            "idx_index_runs_status",
        }
        missing_indexes = expected_indexes - indexes
        if missing_indexes:
            errors.append(f"Missing indexes: {missing_indexes}")
        else:
            print(f"Indexes: OK ({len(indexes)} indexes)")

        close_connection(conn)
    except Exception as exc:
        errors.append(f"Database error: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Health check: OK")
    return 0


def cmd_scan_repo(args: argparse.Namespace) -> int:
    """Scan a repository and persist file records.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    repo_path = args.repo_path

    try:
        # Run scanner
        repo, file_records = scan_repository(repo_path, config)

        # Persist to database (initialize if needed)
        conn = get_connection(db_path)
        try:
            initialize_database(conn)
            upsert_repo(conn, repo)
            upsert_files(conn, file_records)
            conn.commit()
        finally:
            close_connection(conn)

        # Print summary
        if args.json:
            summary = {
                "repo_id": repo.id,
                "repo_name": repo.name,
                "file_count": len(file_records),
                "language": repo.default_language,
            }
            print(json.dumps(summary, indent=2))
        else:
            print(f"Repository scanned successfully")
            print(f"Repo ID: {repo.id}")
            print(f"Files found: {len(file_records)}")
            print(f"Language: {repo.default_language}")

        return 0
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except NotADirectoryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error scanning repository: {exc}", file=sys.stderr)
        return 1


def cmd_extract_ast(args: argparse.Namespace) -> int:
    """Extract AST from a scanned repository.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    repo_path = args.repo_path.resolve()

    try:
        # Get repo ID from name
        repo_id = f"repo:{repo_path.name}"

        # Connect to database
        conn = get_connection(db_path)
        try:
            # Initialize database if needed
            initialize_database(conn)

            # Get repo record
            repo = get_repo_by_id(conn, repo_id)
            if repo is None:
                print(f"Error: Repository not found. Run 'scan-repo' first.", file=sys.stderr)
                return 1

            # Get all Python files for this repo
            file_records = list_files_for_repo(conn, repo_id)

            # Extract AST for each file
            total_nodes = 0
            total_edges = 0
            failures = []

            for file_record in file_records:
                try:
                    nodes, edges, summary = extract_file_graph(repo_id, file_record, repo_path)
                    upsert_nodes(conn, nodes)
                    upsert_edges(conn, edges)
                    total_nodes += len(nodes)
                    total_edges += len(edges)
                except Exception as exc:
                    failures.append((file_record.file_path, str(exc)))

            conn.commit()

            # Print summary
            if args.json:
                output = {
                    "repo_id": repo_id,
                    "files_processed": len(file_records) - len(failures),
                    "failures": len(failures),
                    "nodes_extracted": total_nodes,
                    "edges_extracted": total_edges,
                }
                if failures:
                    output["failure_details"] = [{"file": f, "error": e} for f, e in failures]
                print(json.dumps(output, indent=2))
            else:
                print(f"AST extraction complete")
                print(f"Repo ID: {repo_id}")
                print(f"Files processed: {len(file_records) - len(failures)}")
                print(f"Nodes extracted: {total_nodes}")
                print(f"Edges extracted: {total_edges}")
                if failures:
                    print(f"Failures: {len(failures)}")
                    for file_path, error in failures:
                        print(f"  - {file_path}: {error}")

            return 0
        finally:
            close_connection(conn)

    except Exception as exc:
        print(f"Error extracting AST: {exc}", file=sys.stderr)
        return 1


def cmd_graph_stats(args: argparse.Namespace) -> int:
    """Show graph statistics for a repository.

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
            stats = get_repo_graph_stats(conn, repo_id)
            
            if args.json:
                print(json.dumps(stats, indent=2))
            else:
                print(f"Graph Statistics for {repo_id}")
                print(f"  Nodes: {stats['node_count']}")
                print(f"    Modules: {stats['module_count']}")
                print(f"    Classes: {stats['class_count']}")
                print(f"    Callables: {stats['callable_count']}")
                print(f"      Local callables: {stats['local_callable_count']}")
                print(f"  Edges: {stats['edge_count']}")
            
            return 0
        finally:
            close_connection(conn)
    except Exception as exc:
        print(f"Error getting graph stats: {exc}", file=sys.stderr)
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
                print(f"Error: Node not found: {node_id}", file=sys.stderr)
                return 1
            
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
    except Exception as exc:
        print(f"Error showing node: {exc}", file=sys.stderr)
        return 1


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

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
