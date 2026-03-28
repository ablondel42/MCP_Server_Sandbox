"""Symbol context model."""

from dataclasses import dataclass, field


@dataclass
class SymbolContext:
    """Context assembled around a focus symbol.
    
    Attributes:
        focus_symbol: The symbol being inspected.
        structural_parent: The containing symbol in the code hierarchy (e.g., class for a method, module for a class).
        structural_children: Symbols directly contained by this symbol (e.g., methods in a class).
        lexical_parent: The enclosing scope for nested declarations (e.g., outer function for a nested function).
        lexical_children: Symbols lexically nested inside this symbol (e.g., nested functions, local classes).
        incoming_edges: Relationships where other symbols reference this symbol.
        outgoing_edges: Relationships where this symbol references other symbols.
        file_siblings: Other symbols defined in the same source file.
        structural_summary: Statistics about this symbol's structural relationships.
        freshness: Timestamps indicating when this context was last updated.
        confidence: Trust scores indicating the reliability of this context data.
    """
    focus_symbol: dict
    structural_parent: dict | None = None
    structural_children: list[dict] = field(default_factory=list)
    lexical_parent: dict | None = None
    lexical_children: list[dict] = field(default_factory=list)
    incoming_edges: list[dict] = field(default_factory=list)
    outgoing_edges: list[dict] = field(default_factory=list)
    file_siblings: list[dict] = field(default_factory=list)
    structural_summary: dict = field(default_factory=dict)
    freshness: dict = field(default_factory=dict)
    confidence: dict = field(default_factory=dict)
