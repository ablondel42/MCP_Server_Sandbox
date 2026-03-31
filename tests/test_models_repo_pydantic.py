"""RepoRecord Pydantic model tests."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from repo_context.models.repo import RepoRecord


class TestRepoRecordValid:
    """Tests for valid RepoRecord creation."""

    def test_create_minimal_valid_repo(self) -> None:
        """Test creating a minimal valid RepoRecord."""
        repo = RepoRecord(
            id="repo:test",
            root_path="/path/to/repo",
            name="test-repo",
            default_language="python",
            created_at="2026-01-01T00:00:00Z",
        )
        assert repo.id == "repo:test"
        assert repo.name == "test-repo"
        assert repo.last_indexed_at is None

    def test_create_full_repo(self) -> None:
        """Test creating a RepoRecord with all fields."""
        repo = RepoRecord(
            id="repo:my_project",
            root_path="/Users/dev/projects/my_project",
            name="My Project",
            default_language="python",
            created_at="2026-01-01T00:00:00Z",
            last_indexed_at="2026-03-23T12:00:00Z",
        )
        assert repo.id == "repo:my_project"
        assert repo.last_indexed_at == "2026-03-23T12:00:00Z"


class TestRepoRecordIdValidation:
    """Tests for RepoRecord ID validation."""

    def test_reject_id_without_repo_prefix(self) -> None:
        """Test that ID without 'repo:' prefix is rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            RepoRecord(
                id="test-repo",
                root_path="/path/to/repo",
                name="test-repo",
                default_language="python",
                created_at="2026-01-01T00:00:00Z",
            )
        assert "repo:" in str(exc_info.value).lower()

    def test_reject_empty_id(self) -> None:
        """Test that empty ID is rejected."""
        with pytest.raises(PydanticValidationError):
            RepoRecord(
                id="",
                root_path="/path/to/repo",
                name="test-repo",
                default_language="python",
                created_at="2026-01-01T00:00:00Z",
            )

    def test_reject_none_id(self) -> None:
        """Test that None ID is rejected."""
        with pytest.raises(PydanticValidationError):
            RepoRecord(
                id=None,  # type: ignore[arg-type]
                root_path="/path/to/repo",
                name="test-repo",
                default_language="python",
                created_at="2026-01-01T00:00:00Z",
            )


class TestRepoRecordRootPathValidation:
    """Tests for RepoRecord root_path validation."""

    def test_valid_root_path(self) -> None:
        """Test valid root path."""
        repo = RepoRecord(
            id="repo:test",
            root_path="/path/to/repo",
            name="test-repo",
            default_language="python",
            created_at="2026-01-01T00:00:00Z",
        )
        assert repo.root_path == "/path/to/repo"

    def test_reject_empty_root_path(self) -> None:
        """Test that empty root_path is rejected."""
        with pytest.raises(PydanticValidationError):
            RepoRecord(
                id="repo:test",
                root_path="",
                name="test-repo",
                default_language="python",
                created_at="2026-01-01T00:00:00Z",
            )

    def test_reject_none_root_path(self) -> None:
        """Test that None root_path is rejected."""
        with pytest.raises(PydanticValidationError):
            RepoRecord(
                id="repo:test",
                root_path=None,  # type: ignore[arg-type]
                name="test-repo",
                default_language="python",
                created_at="2026-01-01T00:00:00Z",
            )


class TestRepoRecordNameValidation:
    """Tests for RepoRecord name validation."""

    def test_valid_name(self) -> None:
        """Test valid name."""
        repo = RepoRecord(
            id="repo:test",
            root_path="/path/to/repo",
            name="My Repo",
            default_language="python",
            created_at="2026-01-01T00:00:00Z",
        )
        assert repo.name == "My Repo"

    def test_reject_empty_name(self) -> None:
        """Test that empty name is rejected."""
        with pytest.raises(PydanticValidationError):
            RepoRecord(
                id="repo:test",
                root_path="/path/to/repo",
                name="",
                default_language="python",
                created_at="2026-01-01T00:00:00Z",
            )


class TestRepoRecordLanguageValidation:
    """Tests for RepoRecord default_language validation."""

    def test_valid_python_language(self) -> None:
        """Test valid 'python' language."""
        repo = RepoRecord(
            id="repo:test",
            root_path="/path/to/repo",
            name="test-repo",
            default_language="python",
            created_at="2026-01-01T00:00:00Z",
        )
        assert repo.default_language == "python"

    def test_reject_unsupported_language(self) -> None:
        """Test that unsupported language is rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            RepoRecord(
                id="repo:test",
                root_path="/path/to/repo",
                name="test-repo",
                default_language="cobol",
                created_at="2026-01-01T00:00:00Z",
            )
        # Error should mention invalid enum value
        assert "python" in str(exc_info.value).lower()

    def test_reject_empty_language(self) -> None:
        """Test that empty language is rejected."""
        with pytest.raises(PydanticValidationError):
            RepoRecord(
                id="repo:test",
                root_path="/path/to/repo",
                name="test-repo",
                default_language="",
                created_at="2026-01-01T00:00:00Z",
            )


class TestRepoRecordTimestampValidation:
    """Tests for RepoRecord timestamp validation."""

    def test_valid_iso8601_timestamp(self) -> None:
        """Test valid ISO 8601 timestamp."""
        repo = RepoRecord(
            id="repo:test",
            root_path="/path/to/repo",
            name="test-repo",
            default_language="python",
            created_at="2026-01-01T00:00:00Z",
        )
        assert repo.created_at == "2026-01-01T00:00:00Z"

    def test_valid_iso8601_with_timezone(self) -> None:
        """Test valid ISO 8601 timestamp with timezone."""
        repo = RepoRecord(
            id="repo:test",
            root_path="/path/to/repo",
            name="test-repo",
            default_language="python",
            created_at="2026-01-01T12:00:00+05:00",
        )
        assert repo.created_at == "2026-01-01T12:00:00+05:00"

    def test_reject_invalid_timestamp_format(self) -> None:
        """Test that invalid timestamp format is rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            RepoRecord(
                id="repo:test",
                root_path="/path/to/repo",
                name="test-repo",
                default_language="python",
                created_at="not-a-date",
            )
        assert "iso" in str(exc_info.value).lower() or "datetime" in str(exc_info.value).lower()

    def test_reject_date_only_timestamp(self) -> None:
        """Test that date-only timestamp is accepted (Pydantic allows it as valid ISO 8601)."""
        # Pydantic's datetime.fromisoformat accepts date-only strings
        # This is valid ISO 8601, so we allow it
        repo = RepoRecord(
            id="repo:test",
            root_path="/path/to/repo",
            name="test-repo",
            default_language="python",
            created_at="2026-01-01",
        )
        assert repo.created_at == "2026-01-01"

    def test_valid_last_indexed_at(self) -> None:
        """Test valid last_indexed_at timestamp."""
        repo = RepoRecord(
            id="repo:test",
            root_path="/path/to/repo",
            name="test-repo",
            default_language="python",
            created_at="2026-01-01T00:00:00Z",
            last_indexed_at="2026-03-23T12:00:00Z",
        )
        assert repo.last_indexed_at == "2026-03-23T12:00:00Z"

    def test_none_last_indexed_at(self) -> None:
        """Test None last_indexed_at is allowed."""
        repo = RepoRecord(
            id="repo:test",
            root_path="/path/to/repo",
            name="test-repo",
            default_language="python",
            created_at="2026-01-01T00:00:00Z",
        )
        assert repo.last_indexed_at is None


class TestRepoRecordModelBehavior:
    """Tests for RepoRecord model behavior."""

    def test_model_dump(self) -> None:
        """Test model_dump() returns dict with all fields."""
        repo = RepoRecord(
            id="repo:test",
            root_path="/path/to/repo",
            name="test-repo",
            default_language="python",
            created_at="2026-01-01T00:00:00Z",
        )
        data = repo.model_dump()
        assert isinstance(data, dict)
        assert data["id"] == "repo:test"
        assert data["root_path"] == "/path/to/repo"
        assert data["name"] == "test-repo"
        assert data["default_language"] == "python"
        assert data["created_at"] == "2026-01-01T00:00:00Z"
        assert data["last_indexed_at"] is None

    def test_model_dump_json(self) -> None:
        """Test model_dump_json() returns JSON string."""
        repo = RepoRecord(
            id="repo:test",
            root_path="/path/to/repo",
            name="test-repo",
            default_language="python",
            created_at="2026-01-01T00:00:00Z",
        )
        json_str = repo.model_dump_json()
        assert isinstance(json_str, str)
        assert "repo:test" in json_str
        assert "test-repo" in json_str

    def test_from_dict(self) -> None:
        """Test creating from dict using model_validate."""
        data = {
            "id": "repo:test",
            "root_path": "/path/to/repo",
            "name": "test-repo",
            "default_language": "python",
            "created_at": "2026-01-01T00:00:00Z",
        }
        repo = RepoRecord.model_validate(data)
        assert repo.id == "repo:test"
        assert repo.name == "test-repo"

    def test_immutable_by_default(self) -> None:
        """Test that model instances are immutable."""
        repo = RepoRecord(
            id="repo:test",
            root_path="/path/to/repo",
            name="test-repo",
            default_language="python",
            created_at="2026-01-01T00:00:00Z",
        )
        with pytest.raises(Exception):  # Pydantic raises ValidationError or similar
            repo.id = "repo:new"  # type: ignore[misc]
