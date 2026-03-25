"""Path manipulation utilities for repository scanning."""

from pathlib import Path


def normalize_repo_root(path: str | Path) -> Path:
    """Normalize and validate a repository root path.
    
    Args:
        path: Path to the repository root.
        
    Returns:
        Resolved absolute path.
        
    Raises:
        FileNotFoundError: If the path does not exist.
        NotADirectoryError: If the path is not a directory.
    """
    resolved = Path(path).resolve()
    
    if not resolved.exists():
        raise FileNotFoundError(f"Repository path does not exist: {resolved}")
    
    if not resolved.is_dir():
        raise NotADirectoryError(f"Repository path is not a directory: {resolved}")
    
    return resolved


def to_relative_path(repo_root: Path, file_path: Path) -> str:
    """Convert an absolute file path to a repo-relative POSIX-style path.
    
    Args:
        repo_root: The repository root directory.
        file_path: The absolute file path.
        
    Returns:
        Repo-relative path as a POSIX-style string.
    """
    relative = file_path.relative_to(repo_root)
    return relative.as_posix()


def to_file_uri(file_path: Path) -> str:
    """Convert a file path to a file:// URI.
    
    Args:
        file_path: The absolute file path.
        
    Returns:
        A valid file:// URI string.
    """
    return file_path.as_uri()


def derive_module_path(repo_root: Path, file_path: Path) -> str:
    """Derive a Python module path from a file's filesystem location.
    
    Args:
        repo_root: The repository root directory.
        file_path: The absolute file path to a .py file.
        
    Returns:
        Python module path (e.g., 'app.services.auth').
    """
    relative = file_path.relative_to(repo_root)
    
    # Remove .py extension
    parts = list(relative.parts)
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    
    # Drop trailing __init__
    if parts[-1] == "__init__":
        parts = parts[:-1]
    
    return ".".join(parts)
