"""Symbol node model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SymbolNode:
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
    scope: Optional[str] = None  # "module", "function", or "class"
    lexical_parent_id: Optional[str] = None  # Immediate lexical parent symbol ID
    last_indexed_at: Optional[str] = None
