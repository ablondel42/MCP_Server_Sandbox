"""LSP query position resolver and file URI lookup."""

import json


def get_reference_query_position(symbol) -> dict:
    """Get the query position for finding references to a symbol.

    Prefers selection_range_json.start (most precise - name only).
    Falls back to range_json.start (full declaration range).

    Args:
        symbol: Symbol dictionary or object with range_json and selection_range_json.

    Returns:
        Position dict with 'line' and 'character' keys.

    Raises:
        ValueError: If symbol has no usable range information.
    """
    
    # Support both dict and object attribute access
    if isinstance(symbol, dict):
        selection_range = symbol.get("selection_range_json")
        range_json = symbol.get("range_json")
        symbol_id = symbol.get("id", "unknown")
    else:
        selection_range = getattr(symbol, "selection_range_json", None)
        range_json = getattr(symbol, "range_json", None)
        symbol_id = getattr(symbol, "id", "unknown")

    # Parse JSON strings if needed
    if isinstance(selection_range, str):
        selection_range = json.loads(selection_range)
    if isinstance(range_json, str):
        range_json = json.loads(range_json)

    if selection_range:
        return selection_range["start"]
    if range_json:
        return range_json["start"]
    raise ValueError(f"Symbol {symbol_id} has no stored range for references query")


def resolve_file_by_uri(conn, uri: str):
    """Resolve a file record by exact URI match.

    Args:
        conn: SQLite connection.
        uri: File URI to look up.

    Returns:
        File record dict or None if not found.
    """
    row = conn.execute(
        "SELECT * FROM files WHERE uri = ? LIMIT 1",
        (uri,),
    ).fetchone()
    return row
