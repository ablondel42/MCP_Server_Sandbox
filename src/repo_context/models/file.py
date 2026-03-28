"""File record model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FileRecord:
    """Represents a tracked source file.
    
    Attributes:
        id: Unique identifier (e.g., "file:src/module.py").
        repo_id: ID of the repository this file belongs to.
        file_path: Repository-relative path using POSIX-style separators.
        uri: File URI (e.g., "file:///path/to/src/module.py").
        module_path: Python module path derived from filesystem (e.g., "src.module").
        language: Programming language (e.g., "python").
        content_hash: SHA-256 hash of file contents with "sha256:" prefix.
        size_bytes: File size in bytes.
        last_modified_at: ISO 8601 timestamp of last filesystem modification.
        last_indexed_at: ISO 8601 timestamp of last indexing operation.
    """

    id: str
    repo_id: str
    file_path: str
    uri: str
    module_path: str
    language: str
    content_hash: str
    size_bytes: int
    last_modified_at: str
    last_indexed_at: Optional[str] = None
