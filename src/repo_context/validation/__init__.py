"""Validation module for input validation, type safety, and error handling."""

from repo_context.validation.exceptions import (
    RepoContextError,
    ValidationError,
    InvalidInputError,
    DatabaseError,
    NotFoundError,
    FilesystemError,
    ParseError,
)

from repo_context.validation.validators import (
    validate_repo_id,
    validate_file_id,
    validate_symbol_id,
    validate_edge_id,
    validate_repo_path,
    validate_db_path,
    validate_file_path,
    validate_confidence,
    validate_kind,
    validate_hash,
    validate_uri,
    sanitize_string,
)

__all__ = [
    # Exceptions
    "RepoContextError",
    "ValidationError",
    "InvalidInputError",
    "DatabaseError",
    "NotFoundError",
    "FilesystemError",
    "ParseError",
    # Validators
    "validate_repo_id",
    "validate_file_id",
    "validate_symbol_id",
    "validate_edge_id",
    "validate_repo_path",
    "validate_db_path",
    "validate_file_path",
    "validate_confidence",
    "validate_kind",
    "validate_hash",
    "validate_uri",
    "sanitize_string",
]
