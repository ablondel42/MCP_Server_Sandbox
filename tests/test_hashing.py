"""Tests for hashing utilities."""

import tempfile
from pathlib import Path

from repo_context.parsing.hashing import sha256_text, sha256_file


def test_sha256_text_basic() -> None:
    """Test sha256_text with basic string."""
    result = sha256_text("hello")
    assert result.startswith("sha256:")
    assert len(result) == 71  # "sha256:" (7) + 64 hex chars


def test_sha256_text_stable() -> None:
    """Test sha256_text produces stable output."""
    result1 = sha256_text("test content")
    result2 = sha256_text("test content")
    assert result1 == result2


def test_sha256_text_different_inputs() -> None:
    """Test sha256_text produces different hashes for different inputs."""
    result1 = sha256_text("hello")
    result2 = sha256_text("world")
    assert result1 != result2


def test_sha256_text_empty() -> None:
    """Test sha256_text with empty string."""
    result = sha256_text("")
    assert result.startswith("sha256:")


def test_sha256_file_basic(tmp_path: Path) -> None:
    """Test sha256_file with basic file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")
    
    result = sha256_file(test_file)
    assert result.startswith("sha256:")


def test_sha256_file_stable(tmp_path: Path) -> None:
    """Test sha256_file produces stable output."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    result1 = sha256_file(test_file)
    result2 = sha256_file(test_file)
    assert result1 == result2


def test_sha256_file_same_content(tmp_path: Path) -> None:
    """Test sha256_file produces same hash for same content."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("same content")
    file2.write_text("same content")
    
    result1 = sha256_file(file1)
    result2 = sha256_file(file2)
    assert result1 == result2


def test_sha256_file_binary(tmp_path: Path) -> None:
    """Test sha256_file with binary content."""
    test_file = tmp_path / "binary.bin"
    test_file.write_bytes(b"\x00\x01\x02\x03")
    
    result = sha256_file(test_file)
    assert result.startswith("sha256:")
