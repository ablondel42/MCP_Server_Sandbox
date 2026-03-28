"""Tests for path manipulation utilities."""

import tempfile
from pathlib import Path

import pytest

from repo_context.parsing.pathing import (
    normalize_repo_root,
    to_relative_path,
    to_file_uri,
    derive_module_path,
)


class TestNormalizeRepoRoot:
    """Tests for normalize_repo_root function."""

    def test_valid_directory(self, tmp_path: Path) -> None:
        """Test with valid directory path."""
        result = normalize_repo_root(tmp_path)
        assert result.is_absolute()
        assert result == tmp_path.resolve()

    def test_string_path(self, tmp_path: Path) -> None:
        """Test with string path."""
        result = normalize_repo_root(str(tmp_path))
        assert result.is_absolute()

    def test_nonexistent_path(self, tmp_path: Path) -> None:
        """Test with nonexistent path raises FileNotFoundError."""
        nonexistent = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError):
            normalize_repo_root(nonexistent)

    def test_file_instead_of_directory(self, tmp_path: Path) -> None:
        """Test with file path raises NotADirectoryError."""
        test_file = tmp_path / "file.txt"
        test_file.write_text("content")
        with pytest.raises(NotADirectoryError):
            normalize_repo_root(test_file)


class TestToRelativePath:
    """Tests for to_relative_path function."""

    def test_basic_relative_path(self, tmp_path: Path) -> None:
        """Test basic relative path conversion."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        file = subdir / "file.py"
        file.write_text("content")
        
        result = to_relative_path(tmp_path, file)
        assert result == "subdir/file.py"

    def test_nested_path(self, tmp_path: Path) -> None:
        """Test with nested directory structure."""
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        file = nested / "file.py"
        file.write_text("content")
        
        result = to_relative_path(tmp_path, file)
        assert result == "a/b/c/file.py"

    def test_posix_style(self, tmp_path: Path) -> None:
        """Test that result uses POSIX-style separators."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        file = subdir / "file.py"
        file.write_text("content")
        
        result = to_relative_path(tmp_path, file)
        assert "\\" not in result


class TestToFileUri:
    """Tests for to_file_uri function."""

    def test_basic_uri(self, tmp_path: Path) -> None:
        """Test basic URI generation."""
        file = tmp_path / "file.py"
        file.write_text("content")
        
        result = to_file_uri(file)
        assert result.startswith("file://")

    def test_uri_contains_path(self, tmp_path: Path) -> None:
        """Test that URI contains the file path."""
        file = tmp_path / "test.py"
        file.write_text("content")
        
        result = to_file_uri(file)
        assert "test.py" in result


class TestDeriveModulePath:
    """Tests for derive_module_path function."""

    def test_regular_module(self, tmp_path: Path) -> None:
        """Test regular Python module."""
        # app/services/auth.py -> app.services.auth
        app_dir = tmp_path / "app"
        services_dir = app_dir / "services"
        services_dir.mkdir(parents=True)
        auth_file = services_dir / "auth.py"
        auth_file.write_text("content")
        
        result = derive_module_path(tmp_path, auth_file)
        assert result == "app.services.auth"

    def test_init_file(self, tmp_path: Path) -> None:
        """Test __init__.py file."""
        # app/__init__.py -> app
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        init_file = app_dir / "__init__.py"
        init_file.write_text("content")
        
        result = derive_module_path(tmp_path, init_file)
        assert result == "app"

    def test_nested_init_file(self, tmp_path: Path) -> None:
        """Test nested __init__.py file."""
        # pkg/subpkg/__init__.py -> pkg.subpkg
        pkg_dir = tmp_path / "pkg"
        subpkg_dir = pkg_dir / "subpkg"
        subpkg_dir.mkdir(parents=True)
        init_file = subpkg_dir / "__init__.py"
        init_file.write_text("content")
        
        result = derive_module_path(tmp_path, init_file)
        assert result == "pkg.subpkg"

    def test_top_level_module(self, tmp_path: Path) -> None:
        """Test top-level module."""
        # main.py -> main
        main_file = tmp_path / "main.py"
        main_file.write_text("content")
        
        result = derive_module_path(tmp_path, main_file)
        assert result == "main"

    def test_private_module(self, tmp_path: Path) -> None:
        """Test private module with underscore prefix."""
        # tools/_internal.py -> tools._internal
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        internal_file = tools_dir / "_internal.py"
        internal_file.write_text("content")
        
        result = derive_module_path(tmp_path, internal_file)
        assert result == "tools._internal"
