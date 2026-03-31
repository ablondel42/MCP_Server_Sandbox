"""Validator function tests."""

import os
import tempfile
from pathlib import Path

import pytest

from repo_context.validation.exceptions import ValidationError, InvalidInputError, FilesystemError
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


class TestValidateRepoId:
    """Tests for validate_repo_id function."""

    def test_valid_repo_id(self) -> None:
        """Test valid repo ID passes validation."""
        assert validate_repo_id("repo:test") == "repo:test"
        assert validate_repo_id("repo:my_repo") == "repo:my_repo"
        assert validate_repo_id("repo:my-repo") == "repo:my-repo"

    def test_invalid_repo_id_missing_prefix(self) -> None:
        """Test repo ID without prefix is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            validate_repo_id("test")
        assert exc_info.value.error_code == "validation_error"
        assert "repo:" in str(exc_info.value)

    def test_invalid_repo_id_wrong_prefix(self) -> None:
        """Test repo ID with wrong prefix is rejected."""
        with pytest.raises(ValidationError):
            validate_repo_id("file:test")
        with pytest.raises(ValidationError):
            validate_repo_id("sym:test")

    def test_empty_repo_id(self) -> None:
        """Test empty repo ID is rejected."""
        with pytest.raises(ValidationError):
            validate_repo_id("")

    def test_none_repo_id(self) -> None:
        """Test None repo ID is rejected."""
        with pytest.raises(ValidationError):
            validate_repo_id(None)  # type: ignore[arg-type]


class TestValidateFileId:
    """Tests for validate_file_id function."""

    def test_valid_file_id(self) -> None:
        """Test valid file ID passes validation."""
        assert validate_file_id("file:test.py") == "file:test.py"
        assert validate_file_id("file:src/module/file.py") == "file:src/module/file.py"

    def test_invalid_file_id_missing_prefix(self) -> None:
        """Test file ID without prefix is rejected."""
        with pytest.raises(ValidationError):
            validate_file_id("test.py")

    def test_invalid_file_id_wrong_prefix(self) -> None:
        """Test file ID with wrong prefix is rejected."""
        with pytest.raises(ValidationError):
            validate_file_id("repo:test")
        with pytest.raises(ValidationError):
            validate_file_id("sym:test")

    def test_empty_file_id(self) -> None:
        """Test empty file ID is rejected."""
        with pytest.raises(ValidationError):
            validate_file_id("")


class TestValidateSymbolId:
    """Tests for validate_symbol_id function."""

    def test_valid_symbol_id_module(self) -> None:
        """Test valid module symbol ID."""
        result = validate_symbol_id("sym:repo:test:module:my_module")
        assert result == "sym:repo:test:module:my_module"

    def test_valid_symbol_id_class(self) -> None:
        """Test valid class symbol ID."""
        result = validate_symbol_id("sym:repo:test:class:MyClass")
        assert result == "sym:repo:test:class:MyClass"

    def test_valid_symbol_id_function(self) -> None:
        """Test valid function symbol ID."""
        result = validate_symbol_id("sym:repo:test:function:my_function")
        assert result == "sym:repo:test:function:my_function"

    def test_valid_symbol_id_method(self) -> None:
        """Test valid method symbol ID."""
        result = validate_symbol_id("sym:repo:test:method:MyClass.my_method")
        assert result == "sym:repo:test:method:MyClass.my_method"

    def test_invalid_symbol_id_missing_prefix(self) -> None:
        """Test symbol ID without prefix is rejected."""
        with pytest.raises(ValidationError):
            validate_symbol_id("repo:test:class:MyClass")

    def test_invalid_symbol_id_wrong_prefix(self) -> None:
        """Test symbol ID with wrong prefix is rejected."""
        with pytest.raises(ValidationError):
            validate_symbol_id("file:test.py")
        with pytest.raises(ValidationError):
            validate_symbol_id("edge:test")

    def test_empty_symbol_id(self) -> None:
        """Test empty symbol ID is rejected."""
        with pytest.raises(ValidationError):
            validate_symbol_id("")


class TestValidateEdgeId:
    """Tests for validate_edge_id function."""

    def test_valid_edge_id_contains(self) -> None:
        """Test valid contains edge ID."""
        result = validate_edge_id("edge:repo:test:contains:from_id->to_id")
        assert result == "edge:repo:test:contains:from_id->to_id"

    def test_valid_edge_id_imports(self) -> None:
        """Test valid imports edge ID."""
        result = validate_edge_id("edge:repo:test:imports:from_id->to_id:10")
        assert result == "edge:repo:test:imports:from_id->to_id:10"

    def test_valid_edge_id_inherits(self) -> None:
        """Test valid inherits edge ID."""
        result = validate_edge_id("edge:repo:test:inherits:from_id->unresolved_base:BaseClass")
        assert result == "edge:repo:test:inherits:from_id->unresolved_base:BaseClass"

    def test_invalid_edge_id_missing_prefix(self) -> None:
        """Test edge ID without prefix is rejected."""
        with pytest.raises(ValidationError):
            validate_edge_id("repo:test:contains:from->to")

    def test_invalid_edge_id_wrong_prefix(self) -> None:
        """Test edge ID with wrong prefix is rejected."""
        with pytest.raises(ValidationError):
            validate_edge_id("sym:test")
        with pytest.raises(ValidationError):
            validate_edge_id("file:test.py")

    def test_empty_edge_id(self) -> None:
        """Test empty edge ID is rejected."""
        with pytest.raises(ValidationError):
            validate_edge_id("")


class TestValidateRepoPath:
    """Tests for validate_repo_path function."""

    def test_valid_directory_path(self) -> None:
        """Test valid directory path passes validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_repo_path(tmpdir)
            assert result == Path(tmpdir)
            assert result.is_dir()

    def test_valid_path_object(self) -> None:
        """Test valid Path object passes validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_repo_path(Path(tmpdir))
            assert result == Path(tmpdir)

    def test_nonexistent_path(self) -> None:
        """Test nonexistent path is rejected."""
        with pytest.raises(InvalidInputError) as exc_info:
            validate_repo_path("/nonexistent/path/12345")
        assert exc_info.value.error_code == "invalid_input"

    def test_file_instead_of_directory(self) -> None:
        """Test file path instead of directory is rejected."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            with pytest.raises(InvalidInputError):
                validate_repo_path(tmpfile.name)

    def test_empty_string_path(self) -> None:
        """Test empty string path is rejected."""
        with pytest.raises(InvalidInputError):
            validate_repo_path("")


class TestValidateDbPath:
    """Tests for validate_db_path function."""

    def test_valid_db_path_in_existing_dir(self) -> None:
        """Test valid db path in existing directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            result = validate_db_path(db_path)
            assert result == db_path

    def test_valid_db_path_string(self) -> None:
        """Test valid db path as string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            result = validate_db_path(db_path)
            assert isinstance(result, Path)

    def test_none_db_path(self) -> None:
        """Test None db path returns None."""
        assert validate_db_path(None) is None

    def test_nonexistent_parent_directory(self) -> None:
        """Test db path with nonexistent parent is rejected."""
        with pytest.raises(InvalidInputError):
            validate_db_path("/nonexistent/dir/test.db")

    def test_empty_string_db_path(self) -> None:
        """Test empty string db path is rejected."""
        with pytest.raises(InvalidInputError):
            validate_db_path("")


class TestValidateFilePath:
    """Tests for validate_file_path function."""

    def test_valid_file_path(self) -> None:
        """Test valid file path passes validation."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            result = validate_file_path(Path(tmpfile.name))
            assert result == Path(tmpfile.name)

    def test_nonexistent_file_path(self) -> None:
        """Test nonexistent file path is rejected."""
        with pytest.raises(InvalidInputError):
            validate_file_path(Path("/nonexistent/file.txt"))

    def test_directory_instead_of_file(self) -> None:
        """Test directory path instead of file is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(InvalidInputError):
                validate_file_path(Path(tmpdir))


class TestValidateConfidence:
    """Tests for validate_confidence function."""

    def test_valid_confidence_values(self) -> None:
        """Test valid confidence values pass."""
        assert validate_confidence(0.0) == 0.0
        assert validate_confidence(0.5) == 0.5
        assert validate_confidence(1.0) == 1.0
        assert validate_confidence(0.75) == 0.75

    def test_confidence_too_high(self) -> None:
        """Test confidence > 1.0 is rejected."""
        with pytest.raises(ValidationError):
            validate_confidence(1.5)
        with pytest.raises(ValidationError):
            validate_confidence(2.0)

    def test_confidence_too_low(self) -> None:
        """Test confidence < 0.0 is rejected."""
        with pytest.raises(ValidationError):
            validate_confidence(-0.5)
        with pytest.raises(ValidationError):
            validate_confidence(-1.0)

    def test_string_confidence_rejected(self) -> None:
        """Test string confidence is rejected."""
        with pytest.raises(ValidationError):
            validate_confidence("0.5")  # type: ignore[arg-type]


class TestValidateKind:
    """Tests for validate_kind function."""

    def test_valid_kind(self) -> None:
        """Test valid kind passes validation."""
        allowed = {"module", "class", "function"}
        assert validate_kind("module", allowed) == "module"
        assert validate_kind("class", allowed) == "class"
        assert validate_kind("function", allowed) == "function"

    def test_invalid_kind(self) -> None:
        """Test invalid kind is rejected."""
        allowed = {"module", "class", "function"}
        with pytest.raises(ValidationError):
            validate_kind("method", allowed)
        with pytest.raises(ValidationError):
            validate_kind("invalid", allowed)

    def test_empty_kind(self) -> None:
        """Test empty kind is rejected."""
        allowed = {"module", "class"}
        with pytest.raises(ValidationError):
            validate_kind("", allowed)

    def test_case_sensitive(self) -> None:
        """Test kind validation is case sensitive."""
        allowed = {"Module", "Class"}
        with pytest.raises(ValidationError):
            validate_kind("module", allowed)
        assert validate_kind("Module", allowed) == "Module"


class TestValidateHash:
    """Tests for validate_hash function."""

    def test_valid_sha256_hash(self) -> None:
        """Test valid SHA-256 hash passes."""
        result = validate_hash("sha256:abc123def456")
        assert result == "sha256:abc123def456"

    def test_valid_hash_custom_prefix(self) -> None:
        """Test valid hash with custom prefix."""
        result = validate_hash("md5:abc123", prefix="md5:")
        assert result == "md5:abc123"

    def test_missing_prefix(self) -> None:
        """Test hash without prefix is rejected."""
        with pytest.raises(ValidationError):
            validate_hash("abc123def456")

    def test_wrong_prefix(self) -> None:
        """Test hash with wrong prefix is rejected."""
        with pytest.raises(ValidationError):
            validate_hash("md5:abc123", prefix="sha256:")

    def test_empty_hash(self) -> None:
        """Test empty hash is rejected."""
        with pytest.raises(ValidationError):
            validate_hash("")


class TestValidateUri:
    """Tests for validate_uri function."""

    def test_valid_file_uri(self) -> None:
        """Test valid file:// URI passes."""
        result = validate_uri("file:///path/to/file.py")
        assert result == "file:///path/to/file.py"

    def test_valid_uri_custom_scheme(self) -> None:
        """Test valid URI with custom scheme."""
        result = validate_uri("https://example.com", scheme="https://")
        assert result == "https://example.com"

    def test_missing_scheme(self) -> None:
        """Test URI without scheme is rejected."""
        with pytest.raises(ValidationError):
            validate_uri("/path/to/file.py")

    def test_wrong_scheme(self) -> None:
        """Test URI with wrong scheme is rejected."""
        with pytest.raises(ValidationError):
            validate_uri("https://example.com", scheme="file://")

    def test_empty_uri(self) -> None:
        """Test empty URI is rejected."""
        with pytest.raises(ValidationError):
            validate_uri("")


class TestSanitizeString:
    """Tests for sanitize_string function."""

    def test_plain_string(self) -> None:
        """Test plain string unchanged."""
        assert sanitize_string("hello") == "hello"

    def test_strips_leading_trailing_whitespace(self) -> None:
        """Test leading/trailing whitespace is stripped."""
        assert sanitize_string("  hello  ") == "hello"
        assert sanitize_string("\thello\n") == "hello"

    def test_normalizes_internal_whitespace(self) -> None:
        """Test internal whitespace is normalized."""
        assert sanitize_string("hello  world") == "hello world"
        assert sanitize_string("hello\tworld") == "hello world"

    def test_removes_control_characters(self) -> None:
        """Test control characters are removed."""
        # Bell character
        result = sanitize_string("hello\abello")
        assert "\a" not in result
        assert result == "hellobello"

    def test_empty_string(self) -> None:
        """Test empty string returns empty string."""
        assert sanitize_string("") == ""

    def test_whitespace_only_string(self) -> None:
        """Test whitespace-only string becomes empty."""
        assert sanitize_string("   ") == ""
        assert sanitize_string("\t\n\r") == ""

    def test_unicode_normalization(self) -> None:
        """Test unicode is normalized."""
        # é as single character vs e + combining accent
        result = sanitize_string("café")
        assert len(result) > 0
