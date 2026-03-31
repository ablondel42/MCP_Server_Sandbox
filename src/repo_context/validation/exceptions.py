"""Validation exception hierarchy."""

from typing import Any


class RepoContextError(Exception):
    """Base exception for all repo-context errors.
    
    All custom exceptions in this package inherit from this base class.
    This allows catching all repo-context errors with a single except clause.
    
    Attributes:
        message: Human-readable error message.
        error_code: Machine-readable error code for error handling.
        context: Additional debugging information (repo_id, file_path, etc.).
    """
    
    error_code: str = "unknown_error"
    
    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Initialize the exception.
        
        Args:
            message: Human-readable error message.
            context: Optional dictionary with additional context information.
        """
        super().__init__(message)
        self.message = message
        self.context = context if context is not None else {}
    
    def __str__(self) -> str:
        """Return string representation of the exception."""
        return self.message
    
    def __repr__(self) -> str:
        """Return repr of the exception."""
        return f"{self.__class__.__name__}({self.message!r}, context={self.context!r})"


class ValidationError(RepoContextError):
    """Raised when data validation fails.
    
    Use this exception when:
    - A field value doesn't match expected format
    - A required field is missing
    - A value is out of allowed range
    - Type coercion fails
    """
    
    error_code = "validation_error"


class InvalidInputError(RepoContextError):
    """Raised when user/CLI input is invalid.
    
    Use this exception when:
    - A file path doesn't exist
    - A directory path is actually a file
    - CLI arguments are malformed
    - User input fails validation
    """
    
    error_code = "invalid_input"


class DatabaseError(RepoContextError):
    """Raised when database operations fail.
    
    Use this exception when:
    - A SQL query fails
    - A constraint is violated
    - Connection to database fails
    - Transaction rollback occurs
    """
    
    error_code = "database_error"


class NotFoundError(RepoContextError):
    """Raised when a resource is not found.
    
    Use this exception when:
    - A symbol ID doesn't exist in the database
    - A repository is not indexed
    - A file record is missing
    - An edge cannot be found
    """
    
    error_code = "not_found"


class FilesystemError(RepoContextError):
    """Raised when filesystem operations fail.
    
    Use this exception when:
    - A file cannot be read
    - A directory cannot be accessed
    - Permission is denied
    - Path resolution fails
    """
    
    error_code = "filesystem_error"


class ParseError(RepoContextError):
    """Raised when parsing/AST extraction fails.
    
    Use this exception when:
    - Python source code has syntax errors
    - AST parsing fails
    - Source encoding is invalid
    - Module cannot be parsed
    """
    
    error_code = "parse_error"
