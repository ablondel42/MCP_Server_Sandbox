"""CLI main entry point."""

import argparse
import sys

from repo_context.config import get_config
from repo_context.logging_config import get_logger
from repo_context.mcp import run_server
from repo_context.indexing import watch_repo

logger = get_logger("cli.main")





def cmd_serve_mcp(args: argparse.Namespace) -> int:
    """Start the MCP server on stdio transport.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """

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
