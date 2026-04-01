"""LSP protocol helpers using lsprotocol types."""

from lsprotocol import types as lsp


def build_references_params(uri: str, line: int, character: int, include_declaration: bool = False):
    """Build ReferenceParams for textDocument/references request."""
    return lsp.ReferenceParams(
        text_document=lsp.TextDocumentIdentifier(uri=uri),
        position=lsp.Position(line=line, character=character),
        context=lsp.ReferenceContext(include_declaration=include_declaration),
    )


def normalize_location(location) -> dict:
    """Normalize an LSP location to a consistent dict shape."""
    if isinstance(location, dict):
        return {
            "uri": location["uri"],
            "range": location["range"],
        }
    return {
        "uri": location.uri,
        "range": {
            "start": {
                "line": location.range.start.line,
                "character": location.range.start.character,
            },
            "end": {
                "line": location.range.end.line,
                "character": location.range.end.character,
            },
        },
    }
