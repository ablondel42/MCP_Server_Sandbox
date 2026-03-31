"""Symbol node model."""

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from repo_context.constants import (
    VALID_SYMBOL_KINDS,
    VALID_SCOPES,
)


class SymbolNode(BaseModel):
    """Represents a symbol node in the graph (module, class, function, method).

    Attributes:
        id: Unique symbol identifier (e.g., "sym:repo:module:path").
        repo_id: ID of the repository this symbol belongs to.
        file_id: ID of the file containing this symbol.
        language: Programming language (e.g., "python").
        kind: Symbol type (module, class, function, async_function, method, async_method, local_function, local_async_function).
        name: Simple symbol name (e.g., "AuthService").
        qualified_name: Full dotted path (e.g., "auth.service.AuthService").
        uri: File URI where the symbol is defined.
        content_hash: SHA-256 hash of the symbol's source code.
        semantic_hash: SHA-256 hash representing symbol's semantic meaning.
        source: Data source (e.g., "python-ast", "lsp").
        confidence: Trust score for this symbol's data (0.0 to 1.0).
        payload_json: JSON string with type-specific metadata.
        range_json: JSON string with full declaration range (zero-based).
        selection_range_json: JSON string with name-focused range (zero-based).
        parent_id: ID of the containing symbol (None for modules).
        visibility_hint: Visibility indicator ("public" or "private_like").
        doc_summary: Short docstring summary extracted from source.
        scope: Where the symbol lives ("module", "class", or "function").
        lexical_parent_id: ID of the enclosing scope for nested declarations.
        last_indexed_at: ISO 8601 timestamp of last indexing operation.
    """

    model_config = {"frozen": True}

    id: str = Field(..., min_length=1, pattern=r"^sym:.+")
    repo_id: str = Field(..., min_length=1, pattern=r"^repo:.+")
    file_id: str = Field(..., min_length=1, pattern=r"^file:.+")
    language: str = Field(default="python")
    kind: Literal[
        "module",
        "class",
        "function",
        "async_function",
        "method",
        "async_method",
        "local_function",
        "local_async_function",
    ]
    name: str = Field(..., min_length=1, max_length=256)
    qualified_name: str = Field(..., min_length=1)
    uri: str = Field(..., pattern=r"^file://")
    content_hash: str = Field(default="")
    semantic_hash: str = Field(default="")
    source: str = Field(default="python-ast")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    payload_json: str = Field(default="{}")
    range_json: str | None = None
    selection_range_json: str | None = None
    parent_id: str | None = None
    visibility_hint: str | None = None
    doc_summary: str | None = None
    scope: Literal["module", "class", "function"] | None = None
    lexical_parent_id: str | None = None
    last_indexed_at: str | None = None

    @field_validator("payload_json", "range_json", "selection_range_json", mode="before")
    @classmethod
    def normalize_json_fields(cls, v: Any) -> str | None:
        """Normalize JSON fields - accept dict or string, always return string."""
        if v is None:
            return None
        if isinstance(v, str):
            return v
        # Convert dict/list to JSON string
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
