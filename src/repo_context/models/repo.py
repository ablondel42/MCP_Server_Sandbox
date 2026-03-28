"""Repository record model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RepoRecord:
    """Represents a tracked repository.
    
    Attributes:
        id: Unique identifier for this repository (e.g., "repo:MyProject").
        root_path: Absolute path to the repository root on disk.
        name: Human-readable repository name.
        default_language: Primary language of the codebase (e.g., "python").
        created_at: ISO 8601 timestamp when the repository was first indexed.
        last_indexed_at: ISO 8601 timestamp of the most recent indexing operation.
    """

    id: str
    root_path: str
    name: str
    default_language: str
    created_at: str
    last_indexed_at: Optional[str] = None
