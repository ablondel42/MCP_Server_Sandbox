"""Symbol node model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SymbolNode:
    """Represents a symbol node in the graph (module, class, function, method)."""

    id: str
    repo_id: str
    file_id: str
    language: str
    kind: str
    name: str
    qualified_name: str
    uri: str
    content_hash: str
    semantic_hash: str
    source: str
    confidence: float
    payload_json: str
    range_json: Optional[str] = None
    selection_range_json: Optional[str] = None
    parent_id: Optional[str] = None
    visibility_hint: Optional[str] = None
    doc_summary: Optional[str] = None
    last_indexed_at: Optional[str] = None
