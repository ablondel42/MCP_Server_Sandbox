"""File change event normalization.

Converts watcher-specific event objects into a stable internal event shape.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_context.config import AppConfig


@dataclass
class FileChangeEvent:
    """Normalized file change event.

    Attributes:
        event_type: One of 'created', 'modified', 'deleted'.
        absolute_path: Absolute filesystem path to the file.
        repo_relative_path: Repository-relative path using POSIX-style separators.
        is_supported: True if the file has a supported extension.
        old_absolute_path: Original path for rename events (optional).
        old_repo_relative_path: Original repo-relative path for renames (optional).
    """
    event_type: str
    absolute_path: str
    repo_relative_path: str
    is_supported: bool
    old_absolute_path: str | None = None
    old_repo_relative_path: str | None = None


def normalize_event(
    raw_event: Any,
    repo_root: Path,
    config: AppConfig,
) -> FileChangeEvent | None:
    """Normalize a raw watcher event into the internal FileChangeEvent shape.

    Args:
        raw_event: Watchdog event object (or similar watcher event).
        repo_root: Absolute path to repository root.
        config: Application configuration with ignore rules.

    Returns:
        Normalized FileChangeEvent, or None if the event should be ignored.
    """
    # Determine event type
    raw_type = _get_raw_event_type(raw_event)
    if raw_type is None:
        return None

    event_type = _map_event_type(raw_type)
    if event_type is None:
        return None

    # Get absolute path
    absolute_path = _get_event_path(raw_event)
    if absolute_path is None:
        return None

    # Compute repo-relative path
    try:
        repo_relative_path = _compute_repo_relative_path(absolute_path, repo_root)
    except ValueError:
        # Path is outside the repo root
        return None

    # Check if path is ignored
    if _is_ignored_path(repo_relative_path, config.ignored_dirs):
        return None

    # Check if file is supported
    is_supported = _is_supported_file(repo_relative_path, config.supported_extensions)

    # Handle renames: model as delete old + create new
    old_absolute_path = None
    old_repo_relative_path = None
    if raw_type == "moved":
        old_absolute_path = _get_event_dest_path(raw_event)
        if old_absolute_path:
            try:
                old_repo_relative_path = _compute_repo_relative_path(old_absolute_path, repo_root)
            except ValueError:
                pass

    return FileChangeEvent(
        event_type=event_type,
        absolute_path=absolute_path,
        repo_relative_path=repo_relative_path,
        is_supported=is_supported,
        old_absolute_path=old_absolute_path,
        old_repo_relative_path=old_repo_relative_path,
    )


def _get_raw_event_type(raw_event: Any) -> str | None:
    """Extract the raw event type string from a watcher event."""
    if hasattr(raw_event, "is_directory") and raw_event.is_directory:
        return None  # Ignore directory events

    if hasattr(raw_event, "is_move"):
        if raw_event.is_move:
            return "moved"
        if raw_event.is_created:
            return "created"
        if raw_event.is_modified:
            return "modified"
        if raw_event.is_deleted:
            return "deleted"

    # Fallback: check event type name
    event_type = type(raw_event).__name__.lower()
    if "created" in event_type:
        return "created"
    if "modified" in event_type or "moved" in event_type:
        return "modified"
    if "deleted" in event_type:
        return "deleted"

    return None


def _map_event_type(raw_type: str) -> str | None:
    """Map raw event type to normalized event type."""
    if raw_type in ("created",):
        return "created"
    if raw_type in ("modified",):
        return "modified"
    if raw_type in ("deleted",):
        return "deleted"
    if raw_type == "moved":
        # Renames are handled as delete + create
        return None
    return None


def _get_event_path(raw_event: Any) -> str | None:
    """Get the absolute path from a watcher event."""
    if hasattr(raw_event, "src_path"):
        return raw_event.src_path
    if hasattr(raw_event, "path"):
        return raw_event.path
    return None


def _get_event_dest_path(raw_event: Any) -> str | None:
    """Get the destination path from a move event."""
    if hasattr(raw_event, "dest_path"):
        return raw_event.dest_path
    return None


def _compute_repo_relative_path(absolute_path: str, repo_root: Path) -> str:
    """Compute the repository-relative path using POSIX-style separators.

    Args:
        absolute_path: Absolute filesystem path.
        repo_root: Absolute path to repository root.

    Returns:
        Repository-relative path with POSIX separators.

    Raises:
        ValueError: If the path is outside the repo root.
    """
    abs_path = Path(absolute_path).resolve()
    root = repo_root.resolve()

    try:
        relative = abs_path.relative_to(root)
        return str(relative).replace("\\", "/")
    except ValueError:
        raise ValueError(f"Path {absolute_path} is outside repo root {repo_root}")


def _is_ignored_path(repo_relative_path: str, ignored_dirs: tuple[str, ...]) -> bool:
    """Check if the path matches any ignore rule.

    Args:
        repo_relative_path: Repository-relative path.
        ignored_dirs: Tuple of directory names to ignore.

    Returns:
        True if the path should be ignored.
    """
    parts = repo_relative_path.split("/")

    # Check if any path component matches an ignored directory
    for part in parts:
        if part in ignored_dirs:
            return True

    # Check temp/swap file patterns
    filename = parts[-1] if parts else ""
    if filename.startswith(".") or filename.endswith("~") or filename.endswith(".swp"):
        return True

    return False


def _is_supported_file(repo_relative_path: str, supported_extensions: tuple[str, ...]) -> bool:
    """Check if the file has a supported extension.

    Args:
        repo_relative_path: Repository-relative path.
        supported_extensions: Tuple of supported file extensions.

    Returns:
        True if the file is supported.
    """
    for ext in supported_extensions:
        if repo_relative_path.endswith(ext):
            return True
    return False
