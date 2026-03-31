"""Validator functions for input validation."""

import os
import unicodedata
from pathlib import Path

from repo_context.validation.exceptions import (
    ValidationError,
    InvalidInputError,
    FilesystemError,
)


def validate_repo_id(value: str) -> str:
    """Validate repo ID format: repo:{name}.
    
    Args:
        value: The repo ID to validate.
        
    Returns:
        The validated repo ID.
        
    Raises:
        ValidationError: If the repo ID format is invalid.
    """
    if not isinstance(value, str):
        raise ValidationError(
            f"Repo ID must be a string, got {type(value).__name__}",
            context={"value": value}
        )
    
    if not value:
        raise ValidationError("Repo ID cannot be empty")
    
    if not value.startswith("repo:"):
        raise ValidationError(
            f"Repo ID must start with 'repo:', got '{value}'",
            context={"value": value}
        )
    
    return value


def validate_file_id(value: str) -> str:
    """Validate file ID format: file:{path}.
    
    Args:
        value: The file ID to validate.
        
    Returns:
        The validated file ID.
        
    Raises:
        ValidationError: If the file ID format is invalid.
    """
    if not isinstance(value, str):
        raise ValidationError(
            f"File ID must be a string, got {type(value).__name__}",
            context={"value": value}
        )
    
    if not value:
        raise ValidationError("File ID cannot be empty")
    
    if not value.startswith("file:"):
        raise ValidationError(
            f"File ID must start with 'file:', got '{value}'",
            context={"value": value}
        )
    
    return value


def validate_symbol_id(value: str) -> str:
    """Validate symbol ID format: sym:{repo}:{kind}:{qualified_name}.
    
    Args:
        value: The symbol ID to validate.
        
    Returns:
        The validated symbol ID.
        
    Raises:
        ValidationError: If the symbol ID format is invalid.
    """
    if not isinstance(value, str):
        raise ValidationError(
            f"Symbol ID must be a string, got {type(value).__name__}",
            context={"value": value}
        )
    
    if not value:
        raise ValidationError("Symbol ID cannot be empty")
    
    if not value.startswith("sym:"):
        raise ValidationError(
            f"Symbol ID must start with 'sym:', got '{value}'",
            context={"value": value}
        )
    
    return value


def validate_edge_id(value: str) -> str:
    """Validate edge ID format: edge:{repo}:{kind}:{from}->{to}.
    
    Args:
        value: The edge ID to validate.
        
    Returns:
        The validated edge ID.
        
    Raises:
        ValidationError: If the edge ID format is invalid.
    """
    if not isinstance(value, str):
        raise ValidationError(
            f"Edge ID must be a string, got {type(value).__name__}",
            context={"value": value}
        )
    
    if not value:
        raise ValidationError("Edge ID cannot be empty")
    
    if not value.startswith("edge:"):
        raise ValidationError(
            f"Edge ID must start with 'edge:', got '{value}'",
            context={"value": value}
        )
    
    return value


def validate_repo_path(value: str | Path) -> Path:
    """Validate repository path exists and is a directory.
    
    Args:
        value: The path to validate (string or Path).
        
    Returns:
        The validated path as a Path object.
        
    Raises:
        InvalidInputError: If the path doesn't exist or is not a directory.
    """
    if not isinstance(value, (str, Path)):
        raise InvalidInputError(
            f"Repository path must be a string or Path, got {type(value).__name__}",
            context={"value_type": type(value).__name__}
        )
    
    if isinstance(value, str):
        if not value:
            raise InvalidInputError("Repository path cannot be empty")
        path = Path(value)
    else:
        path = value
    
    if not path.exists():
        raise InvalidInputError(
            f"Repository path does not exist: {path}",
            context={"path": str(path)}
        )
    
    if not path.is_dir():
        raise InvalidInputError(
            f"Repository path must be a directory, got file: {path}",
            context={"path": str(path)}
        )
    
    return path


def validate_db_path(value: str | Path | None) -> Path | None:
    """Validate database path parent directory is writable.
    
    Args:
        value: The database path to validate (string, Path, or None).
        
    Returns:
        The validated path as a Path object, or None if input is None.
        
    Raises:
        InvalidInputError: If the parent directory doesn't exist or is not writable.
    """
    if value is None:
        return None
    
    if not isinstance(value, (str, Path)):
        raise InvalidInputError(
            f"Database path must be a string, Path, or None, got {type(value).__name__}",
            context={"value_type": type(value).__name__}
        )
    
    if isinstance(value, str):
        if not value:
            raise InvalidInputError("Database path cannot be empty")
        path = Path(value)
    else:
        path = value
    
    # Get the parent directory (or the path itself if it's a directory)
    if path.suffix:  # Has extension, likely a file path
        parent_dir = path.parent
    else:
        parent_dir = path
    
    if not parent_dir.exists():
        raise InvalidInputError(
            f"Database parent directory does not exist: {parent_dir}",
            context={"path": str(path), "parent": str(parent_dir)}
        )
    
    if not os.access(parent_dir, os.W_OK):
        raise InvalidInputError(
            f"Database parent directory is not writable: {parent_dir}",
            context={"path": str(path), "parent": str(parent_dir)}
        )
    
    return path


def validate_file_path(value: Path) -> Path:
    """Validate file path exists and is readable.
    
    Args:
        value: The file path to validate.
        
    Returns:
        The validated path.
        
    Raises:
        InvalidInputError: If the file doesn't exist or is not readable.
    """
    if not isinstance(value, Path):
        raise InvalidInputError(
            f"File path must be a Path, got {type(value).__name__}",
            context={"value_type": type(value).__name__}
        )
    
    if not value.exists():
        raise InvalidInputError(
            f"File path does not exist: {value}",
            context={"path": str(value)}
        )
    
    if not value.is_file():
        raise InvalidInputError(
            f"File path must be a file, got directory: {value}",
            context={"path": str(value)}
        )
    
    if not os.access(value, os.R_OK):
        raise FilesystemError(
            f"File is not readable: {value}",
            context={"path": str(value)}
        )
    
    return value


def validate_confidence(value: float) -> float:
    """Validate confidence is between 0.0 and 1.0.
    
    Args:
        value: The confidence value to validate.
        
    Returns:
        The validated confidence value.
        
    Raises:
        ValidationError: If the confidence is out of range or wrong type.
    """
    if not isinstance(value, (int, float)):
        raise ValidationError(
            f"Confidence must be a number, got {type(value).__name__}",
            context={"value": value, "value_type": type(value).__name__}
        )
    
    if value < 0.0 or value > 1.0:
        raise ValidationError(
            f"Confidence must be between 0.0 and 1.0, got {value}",
            context={"value": value}
        )
    
    return float(value)


def validate_kind(value: str, allowed: set[str]) -> str:
    """Validate value is in allowed set.
    
    Args:
        value: The kind value to validate.
        allowed: Set of allowed kind values.
        
    Returns:
        The validated kind value.
        
    Raises:
        ValidationError: If the kind is not in the allowed set.
    """
    if not isinstance(value, str):
        raise ValidationError(
            f"Kind must be a string, got {type(value).__name__}",
            context={"value": value, "value_type": type(value).__name__}
        )
    
    if not value:
        raise ValidationError("Kind cannot be empty")
    
    if value not in allowed:
        raise ValidationError(
            f"Kind '{value}' not in allowed values: {allowed}",
            context={"value": value, "allowed": sorted(allowed)}
        )
    
    return value


def validate_hash(value: str, prefix: str = "sha256:") -> str:
    """Validate hash format with prefix.
    
    Args:
        value: The hash value to validate.
        prefix: Expected hash prefix (default: "sha256:").
        
    Returns:
        The validated hash value.
        
    Raises:
        ValidationError: If the hash format is invalid.
    """
    if not isinstance(value, str):
        raise ValidationError(
            f"Hash must be a string, got {type(value).__name__}",
            context={"value": value, "value_type": type(value).__name__}
        )
    
    if not value:
        raise ValidationError("Hash cannot be empty")
    
    if not value.startswith(prefix):
        raise ValidationError(
            f"Hash must start with '{prefix}', got '{value}'",
            context={"value": value, "expected_prefix": prefix}
        )
    
    return value


def validate_uri(value: str, scheme: str = "file://") -> str:
    """Validate URI format with expected scheme.
    
    Args:
        value: The URI to validate.
        scheme: Expected URI scheme (default: "file://").
        
    Returns:
        The validated URI.
        
    Raises:
        ValidationError: If the URI format is invalid.
    """
    if not isinstance(value, str):
        raise ValidationError(
            f"URI must be a string, got {type(value).__name__}",
            context={"value": value, "value_type": type(value).__name__}
        )
    
    if not value:
        raise ValidationError("URI cannot be empty")
    
    if not value.startswith(scheme):
        raise ValidationError(
            f"URI must start with '{scheme}', got '{value}'",
            context={"value": value, "expected_scheme": scheme}
        )
    
    return value


def sanitize_string(value: str) -> str:
    """Sanitize a string by stripping whitespace, normalizing unicode, and removing control chars.
    
    Args:
        value: The string to sanitize.
        
    Returns:
        The sanitized string.
        
    Raises:
        ValidationError: If the input is not a string.
    """
    if not isinstance(value, str):
        raise ValidationError(
            f"Expected string, got {type(value).__name__}",
            context={"value": value, "value_type": type(value).__name__}
        )
    
    # Strip leading/trailing whitespace
    result = value.strip()
    
    # Normalize unicode (NFC = canonical composition)
    result = unicodedata.normalize("NFC", result)
    
    # Normalize internal whitespace (replace tabs, newlines, multiple spaces with single space)
    result = " ".join(result.split())
    
    # Remove control characters (characters with category 'Cc')
    result = "".join(
        char for char in result
        if unicodedata.category(char) != "Cc"
    )
    
    return result
