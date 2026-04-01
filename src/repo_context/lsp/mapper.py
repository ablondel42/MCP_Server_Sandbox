"""LSP location mapper - range containment and symbol resolution."""

import json


def _parse_range(range_data):
    """Parse range from JSON string or dict."""
    if range_data is None:
        return None
    if isinstance(range_data, str):
        try:
            return json.loads(range_data)
        except json.JSONDecodeError:
            return None
    return range_data


def _pos_le(a: dict, b: dict) -> bool:
    """Check if position a <= position b."""
    return (a["line"], a["character"]) <= (b["line"], b["character"])


def _pos_ge(a: dict, b: dict) -> bool:
    """Check if position a >= position b."""
    return (a["line"], a["character"]) >= (b["line"], b["character"])


def range_contains(outer: dict, inner: dict) -> bool:
    """Check if outer range contains inner range."""
    return _pos_le(outer["start"], inner["start"]) and _pos_ge(outer["end"], inner["end"])


def _range_span_key(r: dict):
    """Get a sort key for range span (smaller = more specific)."""
    return (
        r["end"]["line"] - r["start"]["line"],
        r["end"]["character"] - r["start"]["character"],
    )


def pick_smallest_containing_symbol(symbols_in_file, usage_range: dict):
    """Find the smallest symbol containing the usage range.

    Prefers nested local functions and local classes when their ranges
    are narrower than outer declarations.

    Args:
        symbols_in_file: List of symbol dicts for a file.
        usage_range: The usage location range.

    Returns:
        The smallest containing symbol dict, or None if none found.
    """
    candidates = []
    for s in symbols_in_file:
        range_json = _parse_range(s.get("range_json"))
        if range_json and range_contains(range_json, usage_range):
            candidates.append((s, range_json))
    
    if not candidates:
        return None

    candidates.sort(
        key=lambda x: (
            _range_span_key(x[1]),
            -(x[0].get("lexical_depth", 0)),
            x[0]["id"],
        )
    )
    return candidates[0][0]


def find_module_node_for_file(symbols_in_file):
    """Find the module node in a list of symbols.

    Args:
        symbols_in_file: List of symbol dicts for a file.

    Returns:
        Module symbol dict or None if not found.
    """
    for symbol in symbols_in_file:
        if symbol.get("kind") == "module":
            return symbol
    return None
