"""AST loader for parsing Python files."""

import ast
from pathlib import Path


def load_file_text(file_path: Path) -> str:
    """Load file content as UTF-8 text.
    
    Args:
        file_path: Path to the Python file.
        
    Returns:
        File content as a string.
        
    Raises:
        FileNotFoundError: If the file does not exist.
        UnicodeDecodeError: If the file cannot be decoded as UTF-8.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def parse_file(text: str) -> ast.Module:
    """Parse Python source text into an AST.
    
    Args:
        text: Python source code as a string.
        
    Returns:
        Parsed ast.Module node.
        
    Raises:
        SyntaxError: If the source contains syntax errors.
    """
    return ast.parse(text)
