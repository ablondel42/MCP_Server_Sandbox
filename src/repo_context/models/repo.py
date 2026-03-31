"""Repository record model."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from repo_context.constants import Language


class RepoRecord(BaseModel):
    """Represents a tracked repository.

    Attributes:
        id: Unique identifier for this repository (e.g., "repo:MyProject").
        root_path: Absolute path to the repository root on disk.
        name: Human-readable repository name.
        default_language: Primary language of the codebase (e.g., "python").
        created_at: ISO 8601 timestamp when the repository was first indexed.
        last_indexed_at: ISO 8601 timestamp of the most recent indexing operation.
    """

    model_config = {"frozen": True}

    id: str = Field(..., min_length=1, pattern=r"^repo:.+")
    root_path: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    default_language: Language = Field(default=Language.PYTHON)
    created_at: str
    last_indexed_at: str | None = None

    @field_validator("created_at", "last_indexed_at")
    @classmethod
    def validate_timestamp(cls, v: str | None) -> str | None:
        """Validate timestamp is ISO 8601 format."""
        if v is None:
            return None
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("Timestamp must be ISO 8601 format (e.g., '2026-01-01T00:00:00Z')")
        return v
