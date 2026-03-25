"""Repository scanner for Python files."""

import os
from datetime import datetime, timezone
from pathlib import Path

from repo_context.models.repo import RepoRecord
from repo_context.models.file import FileRecord
from repo_context.parsing.pathing import (
    normalize_repo_root,
    to_relative_path,
    to_file_uri,
    derive_module_path,
)
from repo_context.parsing.hashing import sha256_file


def should_ignore_dir(name: str, ignored_dirs: tuple[str, ...]) -> bool:
    """Check if a directory name should be ignored.
    
    Args:
        name: Directory name to check.
        ignored_dirs: Tuple of directory names to ignore.
        
    Returns:
        True if the directory should be ignored.
    """
    return name in ignored_dirs


def is_supported_source_file(path: Path, supported_extensions: tuple[str, ...]) -> bool:
    """Check if a file is a supported source file.
    
    Args:
        path: File path to check.
        supported_extensions: Tuple of supported file extensions.
        
    Returns:
        True if the file is a supported source file.
    """
    return path.suffix in supported_extensions


def _utc_now_iso() -> str:
    """Get current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def build_repo_record(repo_root: Path) -> RepoRecord:
    """Build a RepoRecord from a normalized repository root.
    
    Args:
        repo_root: Normalized repository root path.
        
    Returns:
        A new RepoRecord instance.
    """
    now = _utc_now_iso()
    folder_name = repo_root.name
    
    return RepoRecord(
        id=f"repo:{folder_name}",
        root_path=str(repo_root),
        name=folder_name,
        default_language="python",
        created_at=now,
        last_indexed_at=now,
    )


def build_file_record(repo_id: str, repo_root: Path, file_path: Path) -> FileRecord:
    """Build a FileRecord from a file path.
    
    Args:
        repo_id: The repository ID.
        repo_root: Normalized repository root path.
        file_path: Absolute file path.
        
    Returns:
        A new FileRecord instance with all fields populated.
    """
    stat = file_path.stat()
    now = _utc_now_iso()
    
    return FileRecord(
        id=f"file:{to_relative_path(repo_root, file_path)}",
        repo_id=repo_id,
        file_path=to_relative_path(repo_root, file_path),
        uri=to_file_uri(file_path),
        module_path=derive_module_path(repo_root, file_path),
        language="python",
        content_hash=sha256_file(file_path),
        size_bytes=stat.st_size,
        last_modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        last_indexed_at=now,
    )


def scan_repository(repo_root: str | Path, config) -> tuple[RepoRecord, list[FileRecord]]:
    """Scan a repository and return repo and file records.
    
    Args:
        repo_root: Path to the repository root.
        config: Application configuration with ignored_dirs and supported_extensions.
        
    Returns:
        Tuple of (RepoRecord, list of FileRecord sorted by file_path).
        
    Raises:
        FileNotFoundError: If the repo path does not exist.
        NotADirectoryError: If the repo path is not a directory.
    """
    root = normalize_repo_root(repo_root)
    repo = build_repo_record(root)
    results: list[FileRecord] = []
    
    for dirpath, dirnames, filenames in os.walk(root):
        # Ignored directories
        dirnames[:] = [
            d for d in dirnames
            if not should_ignore_dir(d, config.ignored_dirs)
        ]
        
        for filename in filenames:
            file_path = Path(dirpath) / filename
            
            if not is_supported_source_file(file_path, config.supported_extensions):
                continue
            
            results.append(build_file_record(repo.id, root, file_path))
    
    # Sort by file_path
    results.sort(key=lambda x: x.file_path)
    
    return repo, results
