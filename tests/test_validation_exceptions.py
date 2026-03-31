"""Validation exception hierarchy tests."""

import pytest

from repo_context.validation.exceptions import (
    RepoContextError,
    ValidationError,
    InvalidInputError,
    DatabaseError,
    NotFoundError,
    FilesystemError,
    ParseError,
)


class TestRepoContextError:
    """Tests for base RepoContextError exception."""

    def test_create_with_message(self) -> None:
        """Test creating exception with message."""
        exc = RepoContextError("Something went wrong")
        assert str(exc) == "Something went wrong"
        assert exc.message == "Something went wrong"

    def test_create_with_context(self) -> None:
        """Test creating exception with context dict."""
        context = {"repo_id": "repo:test", "file_id": "file:test.py"}
        exc = RepoContextError("Operation failed", context=context)
        assert exc.context == context
        assert exc.context["repo_id"] == "repo:test"

    def test_default_error_code(self) -> None:
        """Test default error code."""
        exc = RepoContextError("Error")
        assert exc.error_code == "unknown_error"

    def test_default_context_is_empty_dict(self) -> None:
        """Test that default context is empty dict, not None."""
        exc = RepoContextError("Error")
        assert exc.context == {}

    def test_can_be_raised_and_caught(self) -> None:
        """Test exception can be raised and caught."""
        with pytest.raises(RepoContextError) as exc_info:
            raise RepoContextError("Test error")
        assert exc_info.value.message == "Test error"

    def test_inherits_from_exception(self) -> None:
        """Test that RepoContextError inherits from Exception."""
        exc = RepoContextError("Error")
        assert isinstance(exc, Exception)


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_create_with_message(self) -> None:
        """Test creating validation error with message."""
        exc = ValidationError("Invalid format")
        assert exc.message == "Invalid format"

    def test_error_code_is_validation_error(self) -> None:
        """Test error code is 'validation_error'."""
        exc = ValidationError("Error")
        assert exc.error_code == "validation_error"

    def test_create_with_context(self) -> None:
        """Test creating validation error with context."""
        context = {"field": "repo_id", "value": "invalid"}
        exc = ValidationError("Invalid repo_id", context=context)
        assert exc.context == context

    def test_is_subclass_of_repo_context_error(self) -> None:
        """Test ValidationError is subclass of RepoContextError."""
        exc = ValidationError("Error")
        assert isinstance(exc, RepoContextError)

    def test_can_be_caught_as_repo_context_error(self) -> None:
        """Test ValidationError can be caught as RepoContextError."""
        with pytest.raises(RepoContextError):
            raise ValidationError("Error")


class TestInvalidInputError:
    """Tests for InvalidInputError exception."""

    def test_create_with_message(self) -> None:
        """Test creating invalid input error with message."""
        exc = InvalidInputError("Path does not exist")
        assert exc.message == "Path does not exist"

    def test_error_code_is_invalid_input(self) -> None:
        """Test error code is 'invalid_input'."""
        exc = InvalidInputError("Error")
        assert exc.error_code == "invalid_input"

    def test_is_subclass_of_repo_context_error(self) -> None:
        """Test InvalidInputError is subclass of RepoContextError."""
        exc = InvalidInputError("Error")
        assert isinstance(exc, RepoContextError)


class TestDatabaseError:
    """Tests for DatabaseError exception."""

    def test_create_with_message(self) -> None:
        """Test creating database error with message."""
        exc = DatabaseError("Constraint violation")
        assert exc.message == "Constraint violation"

    def test_error_code_is_database_error(self) -> None:
        """Test error code is 'database_error'."""
        exc = DatabaseError("Error")
        assert exc.error_code == "database_error"

    def test_is_subclass_of_repo_context_error(self) -> None:
        """Test DatabaseError is subclass of RepoContextError."""
        exc = DatabaseError("Error")
        assert isinstance(exc, RepoContextError)


class TestNotFoundError:
    """Tests for NotFoundError exception."""

    def test_create_with_message(self) -> None:
        """Test creating not found error with message."""
        exc = NotFoundError("Symbol not found")
        assert exc.message == "Symbol not found"

    def test_error_code_is_not_found(self) -> None:
        """Test error code is 'not_found'."""
        exc = NotFoundError("Error")
        assert exc.error_code == "not_found"

    def test_is_subclass_of_repo_context_error(self) -> None:
        """Test NotFoundError is subclass of RepoContextError."""
        exc = NotFoundError("Error")
        assert isinstance(exc, RepoContextError)


class TestFilesystemError:
    """Tests for FilesystemError exception."""

    def test_create_with_message(self) -> None:
        """Test creating filesystem error with message."""
        exc = FilesystemError("Permission denied")
        assert exc.message == "Permission denied"

    def test_error_code_is_filesystem_error(self) -> None:
        """Test error code is 'filesystem_error'."""
        exc = FilesystemError("Error")
        assert exc.error_code == "filesystem_error"

    def test_is_subclass_of_repo_context_error(self) -> None:
        """Test FilesystemError is subclass of RepoContextError."""
        exc = FilesystemError("Error")
        assert isinstance(exc, RepoContextError)


class TestParseError:
    """Tests for ParseError exception."""

    def test_create_with_message(self) -> None:
        """Test creating parse error with message."""
        exc = ParseError("Syntax error in file")
        assert exc.message == "Syntax error in file"

    def test_error_code_is_parse_error(self) -> None:
        """Test error code is 'parse_error'."""
        exc = ParseError("Error")
        assert exc.error_code == "parse_error"

    def test_is_subclass_of_repo_context_error(self) -> None:
        """Test ParseError is subclass of RepoContextError."""
        exc = ParseError("Error")
        assert isinstance(exc, RepoContextError)


class TestExceptionHierarchy:
    """Tests for exception hierarchy relationships."""

    def test_all_exceptions_are_repo_context_errors(self) -> None:
        """Test all custom exceptions are RepoContextError instances."""
        exceptions = [
            ValidationError("Error"),
            InvalidInputError("Error"),
            DatabaseError("Error"),
            NotFoundError("Error"),
            FilesystemError("Error"),
            ParseError("Error"),
        ]
        for exc in exceptions:
            assert isinstance(exc, RepoContextError)

    def test_all_exceptions_are_exceptions(self) -> None:
        """Test all custom exceptions are Exception instances."""
        exceptions = [
            ValidationError("Error"),
            InvalidInputError("Error"),
            DatabaseError("Error"),
            NotFoundError("Error"),
            FilesystemError("Error"),
            ParseError("Error"),
        ]
        for exc in exceptions:
            assert isinstance(exc, Exception)

    def test_can_catch_all_with_repo_context_error(self) -> None:
        """Test all exceptions can be caught as RepoContextError."""
        exceptions_to_test = [
            lambda: ValidationError("Error"),
            lambda: InvalidInputError("Error"),
            lambda: DatabaseError("Error"),
            lambda: NotFoundError("Error"),
            lambda: FilesystemError("Error"),
            lambda: ParseError("Error"),
        ]
        for exc_factory in exceptions_to_test:
            with pytest.raises(RepoContextError):
                raise exc_factory()
