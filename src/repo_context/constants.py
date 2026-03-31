"""Constants and enums for the application."""

from enum import Enum


class Language(str, Enum):
    """Supported programming languages."""

    PYTHON = "python"


# Valid symbol kinds
VALID_SYMBOL_KINDS = {
    "module",
    "class",
    "function",
    "async_function",
    "method",
    "async_method",
    "local_function",
    "local_async_function",
}

# Valid scopes for symbols
VALID_SCOPES = {"module", "class", "function"}

# Valid edge kinds
VALID_EDGE_KINDS = {
    "contains",
    "imports",
    "inherits",
    "SCOPE_PARENT",
    "references",
}

# Edge kind constants
EDGE_KIND_CONTAINS = "contains"
EDGE_KIND_IMPORTS = "imports"
EDGE_KIND_INHERITS = "inherits"
EDGE_KIND_SCOPE_PARENT = "SCOPE_PARENT"
EDGE_KIND_REFERENCES = "references"

# ID format prefixes
PREFIX_REPO = "repo:"
PREFIX_FILE = "file:"
PREFIX_SYMBOL = "sym:"
PREFIX_EDGE = "edge:"

# Hash prefixes
PREFIX_SHA256 = "sha256:"

# URI schemes
SCHEME_FILE = "file://"

# Default values
DEFAULT_LANGUAGE = Language.PYTHON
DEFAULT_SOURCE = "python-ast"
DEFAULT_CONFIDENCE = 1.0
