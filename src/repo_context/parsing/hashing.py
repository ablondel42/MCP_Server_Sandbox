"""Content hashing utilities for repository scanning."""

import hashlib
from pathlib import Path


def sha256_text(text: str) -> str:
    """Compute SHA-256 hash of a text string.
    
    Args:
        text: The text to hash.
        
    Returns:
        Hash string with 'sha256:' prefix.
    """
    hash_obj = hashlib.sha256(text.encode("utf-8"))
    return f"sha256:{hash_obj.hexdigest()}"


def sha256_file(file_path: Path) -> str:
    """Compute SHA-256 hash of a file's contents.
    
    Args:
        file_path: Path to the file to hash.
        
    Returns:
        Hash string with 'sha256:' prefix.
        
    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read.
    """
    hash_obj = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hash_obj.update(chunk)
    
    return f"sha256:{hash_obj.hexdigest()}"
