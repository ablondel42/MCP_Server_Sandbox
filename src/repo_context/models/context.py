"""Symbol context model."""

from pydantic import BaseModel, Field


class SymbolContext(BaseModel):
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

    model_config = {"frozen": False}  # Allow mutation for context assembly

    focus_symbol: dict = Field(..., description="The symbol being inspected")
    structural_parent: dict | None = Field(default=None)
    structural_children: list[dict] = Field(default_factory=list)
    lexical_parent: dict | None = Field(default=None)
    lexical_children: list[dict] = Field(default_factory=list)
    incoming_edges: list[dict] = Field(default_factory=list)
    outgoing_edges: list[dict] = Field(default_factory=list)
    file_siblings: list[dict] = Field(default_factory=list)
    structural_summary: dict = Field(default_factory=dict)
    freshness: dict = Field(default_factory=dict)
    confidence: dict = Field(default_factory=dict)
