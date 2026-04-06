"""CLI main entry point."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from repo_context.config import get_config
from repo_context.logging_config import get_logger
from repo_context.storage import (
    get_connection,
    close_connection,
    initialize_database,
    upsert_repo,
    upsert_files,
    replace_file_graph,
    list_files_for_repo,
    get_repo_by_id,
    list_nodes_for_repo,
    get_node_by_id,
    get_node_by_qualified_name,
    get_file_by_id,
)
from repo_context.graph import (
    get_repo_graph_stats,
    find_symbols_by_name,
    get_symbol,
    get_symbol_by_qualified_name,
    build_reference_stats,
    list_reference_edges_for_target,
    list_referenced_by,
    list_references_from_symbol,
    analyze_symbol_risk,
    analyze_target_set_risk,
    DECISION_SAFE_ENOUGH,
    DECISION_REVIEW_REQUIRED,
    DECISION_HIGH_RISK,
)
from repo_context.context import build_symbol_context
from repo_context.models import SymbolContext
from repo_context.parsing.scanner import scan_repository
from repo_context.parsing.pipeline import extract_file_graph
from repo_context.lsp import PyrightLspClient
from repo_context.lsp.references import enrich_references_for_symbol

logger = get_logger("cli.main")


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


def cmd_run_full(args: argparse.Namespace) -> int:
    """Initialize database, scan repository, extract AST, and refresh LSP references.

    This is the full pipeline: init-db + scan + extract-ast + references.
    Defaults to current working directory if no path is provided.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    repo_path = args.repo_path if args.repo_path else Path.cwd()

    try:
        # Step 1: Initialize database
        conn = get_connection(db_path)
        initialize_database(conn)

        # Step 2: Scan repository
        repo, file_records = scan_repository(repo_path, config)
        upsert_repo(conn, repo)
        upsert_files(conn, file_records)
        conn.commit()

        # Step 3: Extract AST from all files
        total_nodes = 0
        total_edges = 0
        failures = []

        for file_record in file_records:
            try:
                nodes, edges, _ = extract_file_graph(repo.id, file_record, Path(repo_path))
                replace_file_graph(conn, file_record.id, nodes, edges)
                total_nodes += len(nodes)
                total_edges += len(edges)
            except Exception as exc:
                failures.append((file_record.file_path, str(exc)))

        conn.commit()
        
        # Step 4: Refresh LSP references for all symbols
        print("Refreshing LSP references for all symbols...")
        lsp_total_refs = 0
        lsp_success_count = 0
        lsp_error_count = 0
        lsp_available = False
        
        try:
            # Get all non-module symbols
            symbols = list_nodes_for_repo(conn, repo.id)
            refreshable = [s for s in symbols if s['kind'] != 'module']
            
            print(f"  Found {len(refreshable)} symbols to refresh")
            
            with PyrightLspClient() as client:
                # Open all Python files first for better cross-file detection
                python_files = [f for f in file_records if f.file_path.endswith('.py')]
                print(f"  Opening {len(python_files)} Python files...")
                for file_record in python_files:
                    file_path = Path(repo_path) / file_record.file_path
                    if file_path.exists():
                        try:
                            text = file_path.read_text(encoding='utf-8')
                            client.did_open(file_record.uri, text)
                        except Exception:
                            pass
                
                # Refresh references for each symbol
                total_refs = 0
                success_count = 0
                error_count = 0
                
                print(f"  Refreshing references...")
                for i, symbol in enumerate(refreshable):
                    try:
                        # Build target symbol dict with required fields
                        file_rec = next((f for f in file_records if f.id == symbol['file_id']), None)
                        if file_rec is None:
                            continue
                            
                        target_symbol = {
                            'id': symbol['id'],
                            'repo_id': symbol['repo_id'],
                            'file_id': symbol['file_id'],
                            'file_path': file_rec.file_path,
                            'uri': symbol['uri'],
                            'qualified_name': symbol['qualified_name'],
                            'kind': symbol['kind'],
                            'scope': symbol.get('scope'),
                            'range_json': symbol.get('range_json'),
                            'selection_range_json': symbol.get('selection_range_json'),
                            'repo_root': str(Path(repo_path).absolute()),
                        }
                        
                        stats = enrich_references_for_symbol(conn, client, target_symbol, open_all_files=False)
                        lsp_total_refs += stats['reference_count']
                        lsp_success_count += 1
                        
                    except Exception as e:
                        lsp_error_count += 1
                
                lsp_available = True
                print(f"  Symbols processed: {lsp_success_count}/{len(refreshable)}")
                print(f"  Total references: {lsp_total_refs}")
                if lsp_error_count > 0:
                    print(f"  Errors: {lsp_error_count}")
                    
        except FileNotFoundError:
            print("  Warning: LSP server (pyright) not found, skipping reference refresh", file=sys.stderr)
        except Exception as e:
            print(f"  Warning: LSP reference refresh failed: {e}", file=sys.stderr)
        
        close_connection(conn)

        # Print summary
        if args.json:
            output = {
                "db_path": str(db_path),
                "repo_id": repo.id,
                "repo_name": repo.name,
                "files_processed": len(file_records) - len(failures),
                "failures": len(failures),
                "nodes_extracted": total_nodes,
                "edges_extracted": total_edges,
            }
            if failures:
                output["failure_details"] = [{"file": f, "error": e} for f, e in failures]
            print(json.dumps(output, indent=2))
        else:
            print(f"Database initialized at {db_path}")
            print(f"Repository scanned: {repo.name}")
            print(f"  Path: {repo_path}")
            print(f"  Files found: {len(file_records)}")
            print(f"  Nodes extracted: {total_nodes}")
            print(f"  Edges extracted: {total_edges}")
            if lsp_available:
                print(f"  LSP references: {lsp_total_refs} references for {lsp_success_count} symbols")
                if lsp_error_count > 0:
                    print(f"  LSP errors: {lsp_error_count}")
            if failures:
                print(f"  Failures: {len(failures)}")
                for file_path, error in failures[:5]:
                    print(f"    - {file_path}: {error}")
                if len(failures) > 5:
                    print(f"    ... and {len(failures) - 5} more")
            print("Ready for testing!")

        return 0

    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except NotADirectoryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def cmd_run_scan(args: argparse.Namespace) -> int:
    """Initialize database and scan repository (no AST extraction).

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    repo_path = args.repo_path if args.repo_path else Path.cwd()

    try:
        # Step 1: Initialize database
        conn = get_connection(db_path)
        initialize_database(conn)

        # Step 2: Scan repository
        repo, file_records = scan_repository(repo_path, config)
        upsert_repo(conn, repo)
        upsert_files(conn, file_records)
        conn.commit()
        close_connection(conn)

        # Print summary
        if args.json:
            output = {
                "db_path": str(db_path),
                "repo_id": repo.id,
                "repo_name": repo.name,
                "files_processed": len(file_records),
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"Database initialized at {db_path}")
            print(f"Repository scanned: {repo.name}")
            print(f"  Path: {repo_path}")
            print(f"  Files found: {len(file_records)}")
            print("Ready for AST extraction!")

        return 0

    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except NotADirectoryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Handle 'rc run' command with optional subcommand.

    Defaults to 'full' if no subcommand is provided.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    # Default to 'full' if no subcommand
    run_command = getattr(args, 'run_command', None) or 'full'
    
    if run_command == 'full':
        return cmd_run_full(args)
    elif run_command == 'init-db':
        return cmd_init_db(args)
    elif run_command == 'scan':
        return cmd_run_scan(args)
    else:
        print(f"Error: Unknown run command: {run_command}", file=sys.stderr)
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
                    replace_file_graph(conn, file_record.id, nodes, edges)
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

                print(f"\nFocus Symbol:")
                print(f"  Kind: {focus['kind']}")
                print(f"  File: {focus['file_id']}")
                print(f"  Scope: {focus['scope']}")

                print(f"\nStructural Relationships:")
                if context.structural_parent:
                    print(f"  Parent: {context.structural_parent['qualified_name']} ({context.structural_parent['kind']})")
                else:
                    print(f"  Parent: None")
                
                if context.structural_children:
                    print(f"  Children ({len(context.structural_children)}):")
                    for child in context.structural_children[:10]:
                        print(f"    - {child['name']} ({child['kind']})")
                    if len(context.structural_children) > 10:
                        print(f"    ... and {len(context.structural_children) - 10} more")
                else:
                    print(f"  Children: None")

                print(f"\nLexical Relationships:")
                if context.lexical_parent:
                    print(f"  Parent: {context.lexical_parent['qualified_name']} ({context.lexical_parent['kind']})")
                else:
                    print(f"  Parent: None")
                
                if context.lexical_children:
                    print(f"  Children ({len(context.lexical_children)}):")
                    for child in context.lexical_children[:10]:
                        print(f"    - {child['name']} ({child['kind']})")
                    if len(context.lexical_children) > 10:
                        print(f"    ... and {len(context.lexical_children) - 10} more")
                else:
                    print(f"  Children: None")

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

                print(f"\nSummary:")
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
    from repo_context.logging_config import get_logger
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
            from repo_context.storage.files import get_file_by_id
            file_record = get_file_by_id(conn, symbol["file_id"])
            if file_record is None:
                logger.error(f"File not found for symbol: {symbol['file_id']}")
                return 1

            # Get repo root from file path
            from pathlib import Path
            file_path = Path(file_record["file_path"])
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
    except Exception as exc:
        logger.exception("cmd_show_node: Failed to show node")
        raise


def cmd_risk_symbol(args: argparse.Namespace) -> int:
    """Analyze risk for a single symbol.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    symbol_id = args.symbol_id

    try:
        conn = get_connection(db_path)
        try:
            result = analyze_symbol_risk(conn, symbol_id)

            logger.info("Symbol risk analyzed", extra={
                "symbol_id": symbol_id,
                "risk_score": result.risk_score,
                "decision": result.decision,
                "issues": len(result.issues)
            })

            if args.json:
                output = {
                    "symbol_id": symbol_id,
                    "risk_score": result.risk_score,
                    "decision": result.decision,
                    "issues": result.issues,
                    "facts": {
                        "target_count": result.facts.target_count,
                        "symbol_kinds": list(result.facts.symbol_kinds),
                        "reference_counts": result.facts.reference_counts,
                        "touches_public_surface": result.facts.touches_public_surface,
                        "cross_file_impact": result.facts.cross_file_impact,
                        "cross_module_impact": result.facts.cross_module_impact,
                        "inheritance_involved": result.facts.inheritance_involved,
                        "stale_symbols": result.facts.stale_symbols,
                        "low_confidence_symbols": result.facts.low_confidence_symbols,
                    },
                }
                print(json.dumps(output, indent=2))
            else:
                print(f"\nRisk Analysis: {symbol_id}")
                print("=" * 60)
                print(f"Risk Score: {result.risk_score}/100")
                print(f"Decision: {result.decision}")
                if result.issues:
                    print(f"\nIssues ({len(result.issues)}):")
                    for issue in result.issues:
                        print(f"  - {issue}")
                else:
                    print("\nIssues: (none)")

            return 0
        finally:
            close_connection(conn)
    except Exception as exc:
        logger.exception("cmd_risk_symbol: Failed to analyze symbol risk")
        raise


def cmd_risk_targets(args: argparse.Namespace) -> int:
    """Analyze risk for multiple symbols.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    symbol_ids = args.symbol_ids

    try:
        conn = get_connection(db_path)
        try:
            result = analyze_target_set_risk(conn, symbol_ids)

            logger.info("Target set risk analyzed", extra={
                "symbol_count": len(symbol_ids),
                "risk_score": result.risk_score,
                "decision": result.decision,
                "issues": len(result.issues)
            })

            if args.json:
                output = {
                    "symbols": symbol_ids,
                    "risk_score": result.risk_score,
                    "decision": result.decision,
                    "issues": result.issues,
                    "facts": {
                        "target_count": result.facts.target_count,
                        "symbol_kinds": list(result.facts.symbol_kinds),
                        "touches_public_surface": result.facts.touches_public_surface,
                        "cross_file_impact": result.facts.cross_file_impact,
                        "cross_module_impact": result.facts.cross_module_impact,
                        "inheritance_involved": result.facts.inheritance_involved,
                        "stale_symbols": result.facts.stale_symbols,
                    },
                }
                print(json.dumps(output, indent=2))
            else:
                print(f"\nRisk Analysis: {len(symbol_ids)} symbol(s)")
                print("=" * 60)
                print(f"Risk Score: {result.risk_score}/100")
                print(f"Decision: {result.decision}")
                if result.issues:
                    print(f"\nIssues ({len(result.issues)}):")
                    for issue in result.issues:
                        print(f"  - {issue}")
                else:
                    print("\nIssues: (none)")

            return 0
        finally:
            close_connection(conn)
    except Exception as exc:
        logger.exception("cmd_risk_targets: Failed to analyze target set risk")
        raise


def cmd_serve_mcp(args: argparse.Namespace) -> int:
    """Start the MCP server on stdio transport.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from repo_context.mcp import run_server

    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    debug = getattr(args, "debug", False)

    try:
        logger.info("Starting MCP server", extra={"db_path": str(db_path), "debug": debug})
        run_server(db_path=str(db_path), debug=debug)
        return 0
    except Exception as exc:
        logger.exception("cmd_serve_mcp: Failed to start MCP server")
        print(f"Error: Failed to start MCP server: {exc}", file=sys.stderr)
        return 1


def cmd_watch(args: argparse.Namespace) -> int:
    """Watch a repository for file changes and perform incremental updates.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from repo_context.indexing import watch_repo

    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    repo_root = args.repo_root
    debounce_ms = getattr(args, "debounce_ms", 500)
    verbose = getattr(args, "verbose", False)

    try:
        logger.info("Starting watch mode", extra={
            "repo_root": str(repo_root),
            "db_path": str(db_path),
            "debounce_ms": debounce_ms,
            "verbose": verbose,
        })
        watch_repo(
            repo_root=repo_root,
            db_path=str(db_path),
            debounce_ms=debounce_ms,
            verbose=verbose,
        )
        return 0
    except FileNotFoundError as exc:
        logger.exception("cmd_watch: Repository root not found")
        print(f"Error: Repository root not found: {exc}", file=sys.stderr)
        return 1
    except NotADirectoryError as exc:
        logger.exception("cmd_watch: Not a directory")
        print(f"Error: Not a directory: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.exception("cmd_watch: Failed to start watch mode")
        print(f"Error: Failed to start watch mode: {exc}", file=sys.stderr)
        return 1


# ==================== Inspection Commands ====================


def cmd_inspect_file(args: argparse.Namespace) -> int:
    """Inspect tracked file metadata.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    conn = get_connection_for_args(args)
    try:
        repo_id = args.repo_id
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
            print(f"  Context keys: {list(data['data']['context'].keys())}")
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
    from repo_context.mcp.tools import (
        handle_resolve_symbol,
        handle_get_symbol_context,
        handle_get_symbol_references,
        handle_analyze_symbol_risk,
    )

    conn = get_connection_for_args(args)
    try:
        tool_name = args.tool_name
        tool_input = json.loads(args.json_input)

        handlers = {
            "resolve_symbol_tool": handle_resolve_symbol,
            "get_symbol_context_tool": handle_get_symbol_context,
            "get_symbol_references_tool": handle_get_symbol_references,
            "analyze_symbol_risk_tool": handle_analyze_symbol_risk,
        }

        if tool_name not in handlers:
            print(f"Unknown tool: {tool_name}. Available: {list(handlers.keys())}", file=sys.stderr)
            return 1

        handler = handlers[tool_name]
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


def cmd_validate_workflow(args: argparse.Namespace) -> int:
    """Run full workflow validation for a fixture.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from repo_context.validation import run_full_workflow_validation

    conn = get_connection_for_args(args)
    try:
        repo_root = args.repo_root
        fixture_name = args.fixture_name or f"workflow:{repo_root.name}"
        result = run_full_workflow_validation(conn, repo_root, fixture_name)

        if args.json:
            output = {
                "name": result.name,
                "passed": result.passed,
                "checks": result.checks,
                "errors": result.errors,
                "details": result.details,
            }
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print(f"\nWorkflow Validation: {result.name}")
            print(f"  Passed: {result.passed}")
            print(f"  Checks: {len(result.checks)}")
            print(f"  Errors: {len(result.errors)}")
            if result.errors:
                print("\nErrors:")
                for err in result.errors:
                    print(f"  - {err}")
        return 0 if result.passed else 1
    except Exception as exc:
        logger.exception("cmd_validate_workflow: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)


def cmd_validate_symbol_workflow(args: argparse.Namespace) -> int:
    """Run symbol-focused workflow validation.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from repo_context.validation import run_symbol_workflow_validation

    conn = get_connection_for_args(args)
    try:
        symbol_id = args.symbol_id
        result = run_symbol_workflow_validation(conn, symbol_id)

        if args.json:
            output = {
                "name": result.name,
                "passed": result.passed,
                "checks": result.checks,
                "errors": result.errors,
                "details": result.details,
            }
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print(f"\nSymbol Workflow Validation: {result.name}")
            print(f"  Passed: {result.passed}")
            print(f"  Checks: {len(result.checks)}")
            print(f"  Errors: {len(result.errors)}")
            if result.errors:
                print("\nErrors:")
                for err in result.errors:
                    print(f"  - {err}")
        return 0 if result.passed else 1
    except Exception as exc:
        logger.exception("cmd_validate_symbol_workflow: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)


def cmd_debug_reindex_file(args: argparse.Namespace) -> int:
    """Run incremental reindex path for a file.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from repo_context.indexing.incremental import reindex_changed_file

    conn = get_connection_for_args(args)
    try:
        repo_root = Path(args.repo_root)
        file_path = Path(args.file_path)
        if not file_path.is_absolute():
            file_path = repo_root / file_path

        config = get_config()
        summary = reindex_changed_file(conn, repo_root, str(file_path), config)

        if args.json:
            print(json.dumps(summary, indent=2, sort_keys=True))
        else:
            print(f"\nReindex File: {args.file_path}")
            print(f"  Status: {summary['status']}")
            print(f"  Nodes: {summary['node_count']}")
            print(f"  Edges: {summary['edge_count']}")
        return 0
    except Exception as exc:
        logger.exception("cmd_debug_reindex_file: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)


def cmd_debug_delete_file(args: argparse.Namespace) -> int:
    """Run deleted-file cleanup path for a file.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from repo_context.indexing.incremental import handle_deleted_file

    conn = get_connection_for_args(args)
    try:
        repo_id = args.repo_id
        file_path = args.file_path
        summary = handle_deleted_file(conn, repo_id, file_path)

        if args.json:
            print(json.dumps(summary, indent=2, sort_keys=True))
        else:
            print(f"\nDelete File: {file_path}")
            print(f"  Status: {summary['status']}")
            print(f"  Deleted nodes: {summary['deleted_node_count']}")
            print(f"  Deleted edges: {summary['deleted_edge_count']}")
        return 0
    except Exception as exc:
        logger.exception("cmd_debug_delete_file: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)


def cmd_debug_normalize_event(args: argparse.Namespace) -> int:
    """Run event normalization logic for one synthetic event.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from repo_context.indexing.events import FileChangeEvent, normalize_event

    class _FakeEvent:
        def __init__(self, path: str, event_type: str):
            self.src_path = path
            self.is_directory = False
            self._type = event_type

        @property
        def is_created(self):
            return self._type == "created"

        @property
        def is_modified(self):
            return self._type == "modified"

        @property
        def is_deleted(self):
            return self._type == "deleted"

        @property
        def is_move(self):
            return False

    try:
        repo_root = Path(args.repo_root)
        file_path = args.file_path
        event_type = args.event_type

        fake_event = _FakeEvent(file_path, event_type)
        config = get_config()
        normalized = normalize_event(fake_event, repo_root, config)

        if normalized is None:
            data = {"skipped": True, "reason": "Event filtered out (ignored or unsupported)"}
        else:
            data = {
                "event_type": normalized.event_type,
                "absolute_path": normalized.absolute_path,
                "repo_relative_path": normalized.repo_relative_path,
                "is_supported": normalized.is_supported,
            }

        if args.json:
            print(json.dumps(data, indent=2, sort_keys=True))
        else:
            if data.get("skipped"):
                print(f"\nEvent normalized: SKIPPED")
                print(f"  Reason: {data['reason']}")
            else:
                print(f"\nEvent normalized:")
                print(f"  Type: {data['event_type']}")
                print(f"  Path: {data['repo_relative_path']}")
                print(f"  Supported: {data['is_supported']}")
        return 0
    except Exception as exc:
        logger.exception("cmd_debug_normalize_event: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1


# ==================== Helper Functions ====================


def _node_to_dict(node) -> dict:
    """Convert a node to a dictionary.

    Args:
        node: Node dict or object.

    Returns:
        Dictionary representation.
    """
    if isinstance(node, dict):
        return node
    from dataclasses import asdict
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
    from dataclasses import asdict
    return asdict(context)


def _make_dict_json_serializable(d: dict) -> dict:
    """Recursively convert sets in a dict to sorted lists for JSON serialization.

    Args:
        d: Dictionary that may contain sets.

    Returns:
        Dictionary with all sets converted to sorted lists.
    """
    result = {}
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
    from dataclasses import asdict
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
