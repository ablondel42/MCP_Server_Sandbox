"""Watch mode orchestration.

Sets up watchdog observer, routes raw events through normalization
and scheduler, and processes incremental updates.
"""

import sqlite3
import sys
import time
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from repo_context.config import AppConfig, get_config
from repo_context.storage import get_connection, close_connection, initialize_database
from repo_context.logging_config import get_logger
from repo_context.indexing.events import normalize_event, FileChangeEvent
from repo_context.indexing.scheduler import EventScheduler
from repo_context.indexing.incremental import process_event_batch

logger = get_logger("indexing.watch")


class _RepoFileHandler(FileSystemEventHandler):
    """Watchdog event handler that routes file events to the scheduler."""

    def __init__(
        self,
        repo_root: Path,
        config: AppConfig,
        scheduler: EventScheduler,
    ):
        """Initialize the handler.

        Args:
            repo_root: Absolute path to repository root.
            config: Application configuration.
            scheduler: Event scheduler for debounce and batching.
        """
        super().__init__()
        self._repo_root = repo_root
        self._config = config
        self._scheduler = scheduler

    def on_created(self, event):
        self._handle_event(event)

    def on_modified(self, event):
        self._handle_event(event)

    def on_deleted(self, event):
        self._handle_event(event)

    def on_moved(self, event):
        self._handle_event(event)

    def _handle_event(self, event):
        if event.is_directory:
            return

        normalized = normalize_event(event, self._repo_root, self._config)
        if normalized is None:
            return

        if not normalized.is_supported and normalized.event_type != "deleted":
            return

        self._scheduler.submit(normalized)


def watch_repo(
    repo_root: Path,
    config: AppConfig | None = None,
    db_path: str | None = None,
    debounce_ms: int = 500,
    verbose: bool = False,
) -> None:
    """Watch a repository for file changes and perform incremental updates.

    Args:
        repo_root: Absolute path to repository root.
        config: Application configuration (uses default if None).
        db_path: Optional path to database file.
        debounce_ms: Debounce window in milliseconds.
        verbose: Enable verbose logging.

    Raises:
        FileNotFoundError: If repo_root does not exist.
        NotADirectoryError: If repo_root is not a directory.
    """
    repo_root = repo_root.resolve()

    if not repo_root.exists():
        raise FileNotFoundError(f"Repository root not found: {repo_root}")
    if not repo_root.is_dir():
        raise NotADirectoryError(f"Not a directory: {repo_root}")

    cfg = config or get_config()

    logger.info("Starting watch mode", extra={
        "repo_root": str(repo_root),
        "db_path": db_path or str(cfg.db_path),
        "debounce_ms": debounce_ms,
    })

    # Initialize database
    conn = get_connection(db_path or cfg.db_path)
    try:
        initialize_database(conn)
    finally:
        close_connection(conn)

    # Create batch handler
    def on_batch_ready(events: list[FileChangeEvent]) -> None:
        _process_watch_batch(conn_factory, repo_root, events, cfg, verbose)

    scheduler = EventScheduler(
        debounce_ms=debounce_ms,
        on_batch_ready=on_batch_ready,
    )

    # Create watchdog handler
    handler = _RepoFileHandler(repo_root, cfg, scheduler)

    # Set up observer
    observer = Observer()
    observer.schedule(handler, str(repo_root), recursive=True)
    observer.start()

    print(f"Watching {repo_root} for file changes (debounce={debounce_ms}ms)", file=sys.stderr)
    print("Press Ctrl+C to stop.", file=sys.stderr)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watch mode...", file=sys.stderr)
    finally:
        observer.stop()
        observer.join()
        scheduler.stop()
        logger.info("Watch mode stopped")


def conn_factory(db_path: str | None = None):
    """Create a database connection for batch processing."""
    config = get_config()
    conn = get_connection(db_path or config.db_path)
    initialize_database(conn)
    return conn


def _process_watch_batch(
    conn_factory_func,
    repo_root: Path,
    events: list[FileChangeEvent],
    config: AppConfig,
    verbose: bool,
) -> None:
    """Process a batch of file change events.

    Args:
        conn_factory_func: Function that returns a database connection.
        repo_root: Absolute path to repository root.
        events: List of collapsed FileChangeEvent objects.
        config: Application configuration.
        verbose: Enable verbose logging.
    """
    conn = conn_factory_func()
    try:
        results = process_event_batch(conn, repo_root, events, config)

        for result in results:
            status = result.get("status", "unknown")
            file_path = result.get("file_path", "unknown")

            if status == "reindexed":
                node_count = result.get("node_count", 0)
                edge_count = result.get("edge_count", 0)
                invalidated = result.get("invalidated_reference_edge_count", 0)
                msg = f"✓ Reindexed: {file_path} ({node_count} nodes, {edge_count} edges, {invalidated} refs invalidated)"
                print(msg, file=sys.stderr)
                if verbose:
                    logger.info("File reindexed", extra={
                        "file_path": file_path,
                        "node_count": node_count,
                        "edge_count": edge_count,
                        "invalidated_refs": invalidated,
                    })

            elif status == "deleted":
                deleted_nodes = result.get("deleted_node_count", 0)
                deleted_edges = result.get("deleted_edge_count", 0)
                invalidated_symbols = result.get("invalidated_target_symbol_count", 0)
                msg = f"✗ Deleted: {file_path} ({deleted_nodes} nodes, {deleted_edges} edges removed, {invalidated_symbols} symbols invalidated)"
                print(msg, file=sys.stderr)
                if verbose:
                    logger.info("File deleted", extra={
                        "file_path": file_path,
                        "deleted_nodes": deleted_nodes,
                        "deleted_edges": deleted_edges,
                        "invalidated_symbols": invalidated_symbols,
                    })

            elif status == "parse_failed":
                msg = f"⚠ Parse failed: {file_path} (previous graph preserved)"
                print(msg, file=sys.stderr)
                logger.warning("File parse failed during watch", extra={"file_path": file_path})

            elif status == "skipped":
                if verbose:
                    print(f"↷ Skipped: {file_path}", file=sys.stderr)

            elif status == "error":
                msg = f"✗ Error: {file_path} (previous graph preserved)"
                print(msg, file=sys.stderr)
                logger.error("File indexing error during watch", extra={"file_path": file_path})

    finally:
        close_connection(conn)
