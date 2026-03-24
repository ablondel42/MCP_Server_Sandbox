"""File record model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FileRecord:
    """Represents a tracked source file."""

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
