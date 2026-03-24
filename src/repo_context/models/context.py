"""Symbol context model."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SymbolContext:
    """Represents assembled context around a focus symbol."""

    focus_symbol_id: str
    parent_symbol_id: Optional[str] = None
    child_symbol_ids: list[str] = field(default_factory=list)
    outgoing_edge_ids: list[str] = field(default_factory=list)
    incoming_edge_ids: list[str] = field(default_factory=list)
    reference_count: int = 0
    referencing_file_count: int = 0
    freshness_status: str = "unknown"
    confidence_score: float = 0.0
