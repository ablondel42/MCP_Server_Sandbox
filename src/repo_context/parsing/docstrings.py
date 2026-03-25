"""Docstring helpers for extracting documentation summaries."""

import ast


def get_doc_summary(node: ast.AST) -> str | None:
    """Extract a short summary from a node's docstring.
    
    Args:
        node: AST node (Module, ClassDef, FunctionDef, or AsyncFunctionDef).
        
    Returns:
        First short meaningful paragraph or line, or None if no docstring.
    """
    docstring = ast.get_docstring(node)
    
    if docstring is None:
        return None
    
    # Strip leading and trailing whitespace
    docstring = docstring.strip()
    
    if not docstring:
        return None
    
    # Split into lines and find first non-empty meaningful chunk
    lines = docstring.splitlines()
    meaningful_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped:
            meaningful_lines.append(stripped)
        elif meaningful_lines:
            # Stop at first blank line after meaningful content
            break
    
    if not meaningful_lines:
        return None
    
    # Return first short paragraph (first few meaningful lines)
    # Limit to first 3 lines or 200 characters for brevity
    summary = " ".join(meaningful_lines[:3])
    if len(summary) > 200:
        summary = summary[:197] + "..."
    
    return summary
