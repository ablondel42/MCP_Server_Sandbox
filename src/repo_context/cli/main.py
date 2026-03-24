"""CLI main entry point."""

import argparse
import sys
from pathlib import Path

from repo_context.config import get_config
from repo_context.storage import get_connection, close_connection, initialize_database


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
    
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
