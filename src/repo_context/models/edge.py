"""Edge model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Edge:
    """Represents a relationship between two symbol nodes."""

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
