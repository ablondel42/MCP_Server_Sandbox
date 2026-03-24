"""Repository record model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RepoRecord:
    """Represents a tracked repository."""

    id: str
    root_path: str
    name: str
    default_language: str
    created_at: str
    last_indexed_at: Optional[str] = None
