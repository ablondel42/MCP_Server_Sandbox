"""Edge model constants."""

# Structural edge kinds
EDGE_KIND_CONTAINS = "contains"
EDGE_KIND_IMPORTS = "imports"
EDGE_KIND_INHERITS = "inherits"

# Lexical scope edge kind (Phase 03b)
EDGE_KIND_SCOPE_PARENT = "SCOPE_PARENT"

# All valid edge kinds
VALID_EDGE_KINDS = {
    EDGE_KIND_CONTAINS,
    EDGE_KIND_IMPORTS,
    EDGE_KIND_INHERITS,
    EDGE_KIND_SCOPE_PARENT,
}
