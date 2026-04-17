"""Event scheduler with debounce and batching.

Accepts normalized events, deduplicates by repo-relative path,
batches events within a debounce window, and emits ready batches.
"""

import threading
from collections import defaultdict
from typing import Callable

from repo_context.indexing.events import FileChangeEvent


class EventScheduler:
    """Sequential debounce and batching scheduler for file change events.

    Accepts normalized events, deduplicates by repo-relative path,
    and emits ready batches after a configurable debounce window.
    """

    def __init__(
        self,
        debounce_ms: int = 500,
        on_batch_ready: Callable[[list[FileChangeEvent]], None] | None = None,
    ):
        """Initialize the scheduler.

        Args:
            debounce_ms: Debounce window in milliseconds (default 500ms).
            on_batch_ready: Callback invoked when a batch is ready to process.
        """
        self._debounce_sec = debounce_ms / 1000.0
        self._on_batch_ready = on_batch_ready or self._default_batch_handler
        self._pending_events: dict[str, FileChangeEvent] = {}
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._running = True

    def submit(self, event: FileChangeEvent) -> None:
        """Submit a normalized file change event.

        Events with the same repo_relative_path are deduplicated within
        the current debounce window.

        Args:
            event: Normalized file change event.
        """
        with self._lock:
            if not self._running:
                return

            # Deduplicate: latest event for each path wins
            self._pending_events[event.repo_relative_path] = event

            # Reset debounce timer
            if self._timer is not None:
                self._timer.cancel()

            self._timer = threading.Timer(self._debounce_sec, self._emit_batch)
            self._timer.daemon = True
            self._timer.start()

    def stop(self) -> None:
        """Stop the scheduler and emit any pending batch."""
        with self._lock:
            self._running = False
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

        # Emit final batch if any events pending
        if self._pending_events:
            self._emit_batch()

    def _emit_batch(self) -> None:
        """Emit the current batch of events for processing."""
        with self._lock:
            if not self._pending_events:
                return

            events = list(self._pending_events.values())
            self._pending_events.clear()

        # Collapse events by path before emitting
        collapsed = _collapse_events(events)
        self._on_batch_ready(collapsed)

    def _default_batch_handler(self, events: list[FileChangeEvent]) -> None:
        """Default batch handler (no-op if not overridden)."""
        pass


def collapse_events(events: list[FileChangeEvent]) -> list[FileChangeEvent]:
    """Collapse a list of events by repo-relative path.

    Applies deterministic final-state collapse rules:
    - Repeated 'modified' events collapse to one 'modified'
    - 'created' followed by 'modified' collapses to one effective create
    - Latest 'deleted' wins over earlier create or modify events

    Args:
        events: List of normalized file change events.

    Returns:
        Collapsed list with at most one event per repo_relative_path.
    """
    return _collapse_events(events)


def _collapse_events(events: list[FileChangeEvent]) -> list[FileChangeEvent]:
    """Internal collapse implementation."""
    # Group by repo_relative path
    by_path: dict[str, list[FileChangeEvent]] = defaultdict(list)
    for event in events:
        by_path[event.repo_relative_path].append(event)

    collapsed = []
    for path, path_events in by_path.items():
        final = _collapse_path_events(path_events)
        if final is not None:
            collapsed.append(final)

    return collapsed


def _collapse_path_events(events: list[FileChangeEvent]) -> FileChangeEvent | None:
    """Collapse events for a single path to one final effective action.

    Rules:
    - Latest 'deleted' wins over earlier create or modify
    - 'created' + 'modified' = effective create (keep the create event)
    - Repeated 'modified' = one 'modified'
    """
    has_delete = False
    has_create = False
    last_event = events[0]

    for event in events:
        if event.event_type == "deleted":
            has_delete = True
            last_event = event
        elif event.event_type == "created":
            has_create = True
            last_event = event
        elif event.event_type == "modified":
            last_event = event

    # If deleted, return delete event
    if has_delete:
        return FileChangeEvent(
            event_type="deleted",
            absolute_path=last_event.absolute_path,
            repo_relative_path=last_event.repo_relative_path,
            is_supported=last_event.is_supported,
        )

    # If created + modified, return create event (file exists)
    if has_create:
        return FileChangeEvent(
            event_type="created",
            absolute_path=last_event.absolute_path,
            repo_relative_path=last_event.repo_relative_path,
            is_supported=last_event.is_supported,
        )

    # Otherwise, return the last modified event
    return last_event
