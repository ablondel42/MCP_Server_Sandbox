"""File record model."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class FileRecord(BaseModel):
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

    model_config = {"frozen": True}

    id: str = Field(..., min_length=1, pattern=r"^file:.+")
    repo_id: str = Field(..., min_length=1, pattern=r"^repo:.+")
    file_path: str = Field(..., min_length=1)
    uri: str = Field(..., pattern=r"^file://")
    module_path: str = Field(..., min_length=1)
    language: str = Field(default="python")
    content_hash: str = Field(..., pattern=r"^sha256:.+")
    size_bytes: int = Field(..., ge=0)
    last_modified_at: str
    last_indexed_at: str | None = None

    @field_validator("last_modified_at", "last_indexed_at")
    @classmethod
    def validate_timestamp(cls, v: str | None) -> str | None:
        """Validate timestamp is ISO 8601 format."""
        if v is None:
            return None
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("Timestamp must be ISO 8601 format")
        return v
