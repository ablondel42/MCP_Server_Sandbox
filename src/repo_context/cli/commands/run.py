"""CLI main entry point."""

import argparse
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
)
from repo_context.parsing.scanner import scan_repository
from repo_context.parsing.pipeline import extract_file_graph
from repo_context.lsp import PyrightLspClient
from repo_context.lsp.references import enrich_references_for_symbol
from .maintenance import cmd_init_db

logger = get_logger("cli.main")





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
                        except Exception as e:
                            logger.warning(f"Failed to open file {file_path} in LSP: {e}")
                
                # Refresh references for each symbol

                print("  Refreshing references...")
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
                        
                    except Exception:
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
                for fail_path, error in failures[:5]:
                    print(f"    - {fail_path}: {error}")
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
            print("Repository scanned successfully")
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
                print("Error: Repository not found. Run 'scan-repo' first.", file=sys.stderr)
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
                print("AST extraction complete")
                print(f"Repo ID: {repo_id}")
                print(f"Files processed: {len(file_records) - len(failures)}")
                print(f"Nodes extracted: {total_nodes}")
                print(f"Edges extracted: {total_edges}")
                if failures:
                    print(f"Failures: {len(failures)}")
                    for fail_path, error in failures:
                        print(f"  - {fail_path}: {error}")

            return 0
        finally:
            close_connection(conn)

    except Exception as exc:
        print(f"Error extracting AST: {exc}", file=sys.stderr)
        return 1
