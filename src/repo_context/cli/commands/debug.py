"""CLI main entry point."""

import argparse
import json
import sys
from pathlib import Path

from repo_context.config import get_config
from repo_context.logging_config import get_logger
from repo_context.storage import (
    close_connection,
)



from ..utils import get_connection_for_args
from repo_context.indexing.incremental import reindex_changed_file
from repo_context.indexing.incremental import handle_deleted_file
from repo_context.indexing.events import normalize_event



logger = get_logger("cli.main")

def cmd_debug_reindex_file(args: argparse.Namespace) -> int:
    """Run incremental reindex path for a file.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """

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
                print("\nEvent normalized: SKIPPED")
                print(f"  Reason: {data['reason']}")
            else:
                print("\nEvent normalized:")
                print(f"  Type: {data['event_type']}")
                print(f"  Path: {data['repo_relative_path']}")
                print(f"  Supported: {data['is_supported']}")
        return 0
    except Exception as exc:
        logger.exception("cmd_debug_normalize_event: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
