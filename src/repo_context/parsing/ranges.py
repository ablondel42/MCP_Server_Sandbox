"""Range helpers for converting AST locations to zero-based ranges."""

import ast
from typing import Any


def to_zero_based_line(line: int | None) -> int | None:
    """Convert AST one-based line number to zero-based.
    
    Args:
        line: One-based line number from AST.
        
    Returns:
        Zero-based line number, or None if input is None.
    """
    if line is None:
        return None
    return line - 1


def make_position(line: int | None, character: int | None) -> dict[str, int] | None:
    """Create a position dictionary.
    
    Args:
        line: Zero-based line number.
        character: Zero-based character offset.
        
    Returns:
        Position dict with 'line' and 'character' keys, or None if either is None.
    """
    if line is None or character is None:
        return None
    return {"line": line, "character": character}


def make_range(node: ast.AST) -> dict[str, Any] | None:
    """Create a range dictionary from an AST node.
    
    Args:
        node: AST node with location information.
        
    Returns:
        Range dict with 'start' and 'end' positions, or None if metadata missing.
    """
    lineno = getattr(node, "lineno", None)
    col_offset = getattr(node, "col_offset", None)
    end_lineno = getattr(node, "end_lineno", None)
    end_col_offset = getattr(node, "end_col_offset", None)
    
    if lineno is None or col_offset is None:
        return None
    
    start = make_position(to_zero_based_line(lineno), col_offset)
    end = make_position(to_zero_based_line(end_lineno), end_col_offset)
    
    if start is None or end is None:
        return None
    
    return {"start": start, "end": end}


def make_name_selection_range(node: ast.AST, source_line: str | None = None) -> dict[str, Any] | None:
    """Create a name-focused selection range from an AST node.

    For ClassDef, FunctionDef, and AsyncFunctionDef, returns a narrower
    range focused on the declaration name.

    Args:
        node: AST node (ClassDef, FunctionDef, or AsyncFunctionDef).
        source_line: Optional source line text for precise name positioning.

    Returns:
        Selection range dict, or None if metadata missing.
    """
    lineno = getattr(node, "lineno", None)
    col_offset = getattr(node, "col_offset", None)

    if lineno is None or col_offset is None:
        return None

    name = getattr(node, "name", None)
    if name is None:
        return None

    # If we have the source line, find the actual name position
    # Otherwise fall back to using col_offset (which may include 'def ' or 'class ')
    if source_line is not None:
        # Find the name in the source line
        name_pos = source_line.find(name, col_offset)
        if name_pos >= 0:
            start_char = name_pos
        else:
            start_char = col_offset
    else:
        # Fallback: assume name starts at col_offset
        # This is wrong for def/class but works as a fallback
        start_char = col_offset

    name_len = len(name)
    start = make_position(to_zero_based_line(lineno), start_char)
    end = make_position(to_zero_based_line(lineno), start_char + name_len)

    if start is None or end is None:
        return None

    return {"start": start, "end": end}
