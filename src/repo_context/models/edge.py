"""Edge model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Edge:
    """Represents a relationship between two symbol nodes.
    
    Attributes:
        id: Unique edge identifier.
        repo_id: ID of the repository this edge belongs to.
        kind: Edge type ("contains", "imports", "inherits", "SCOPE_PARENT").
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

    id: str
    repo_id: str
    kind: str
    from_id: str
    to_id: str
    source: str
    confidence: float
    payload_json: str
    evidence_file_id: Optional[str] = None
    evidence_uri: Optional[str] = None
    evidence_range_json: Optional[str] = None
    last_indexed_at: Optional[str] = None
