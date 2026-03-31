"""Edge model."""

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from repo_context.constants import VALID_EDGE_KINDS


class Edge(BaseModel):
    """Represents a relationship between two symbol nodes.

    Attributes:
        id: Unique edge identifier.
        repo_id: ID of the repository this edge belongs to.
        kind: Edge type ("contains", "imports", "inherits", "SCOPE_PARENT", "references").
        from_id: ID of the source symbol.
        to_id: ID of the target symbol.
        source: Data source (e.g., "python-ast", "lsp").
        confidence: Trust score for this edge (0.0 to 1.0).
        payload_json: JSON string with edge-specific metadata.
        evidence_file_id: ID of the file providing evidence for this edge.
        evidence_uri: File URI where this relationship was observed.
        evidence_range_json: JSON string with source code range of the relationship.
        last_indexed_at: ISO 8601 timestamp of last indexing operation.
    """

    model_config = {"frozen": True}

    id: str = Field(..., min_length=1)  # Allow any non-empty ID for tests, production should use edge:...
    repo_id: str = Field(..., min_length=1)  # Allow any non-empty ID for tests
    kind: Literal["contains", "imports", "inherits", "SCOPE_PARENT", "references"]
    from_id: str = Field(..., min_length=1)
    to_id: str = Field(..., min_length=1)
    source: str = Field(default="python-ast")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    payload_json: str = Field(default="{}")
    evidence_file_id: str | None = None
    evidence_uri: str | None = None
    evidence_range_json: str | None = None
    last_indexed_at: str | None = None

    @field_validator("payload_json", "evidence_range_json", mode="before")
    @classmethod
    def normalize_json_fields(cls, v: Any) -> str | None:
        """Normalize JSON fields - accept dict or string, always return string."""
        if v is None:
            return None
        if isinstance(v, str):
            return v
        return json.dumps(v, sort_keys=True)

    @field_validator("last_indexed_at")
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
