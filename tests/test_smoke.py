"""Smoke tests for basic imports and configuration."""

import subprocess
import sys


def test_import_package() -> None:
    """Test that the package can be imported."""
    import repo_context  # noqa: F401


def test_import_config() -> None:
    """Test that config can be imported and used."""
    from repo_context.config import get_config

    config = get_config()
    assert config.app_name == "repo-context-mcp"
    assert config.debug is False
    assert ".git" in config.ignored_dirs
    assert ".py" in config.supported_extensions


def test_import_models() -> None:
    """Test that all models can be imported."""
    from repo_context.models import (
        Position,
        Range,
        RepoRecord,
        FileRecord,
        SymbolNode,
        Edge,
        SymbolContext,
        PlanAssessment,
        to_json,
        from_json,
    )

    # Verify they are classes/functions
    assert Position is not None
    assert Range is not None
    assert RepoRecord is not None
    assert FileRecord is not None
    assert SymbolNode is not None
    assert Edge is not None
    assert SymbolContext is not None
    assert PlanAssessment is not None
    assert callable(to_json)
    assert callable(from_json)


def test_cli_module_help() -> None:
    """Test that CLI module can be invoked with --help."""
    result = subprocess.run(
        [sys.executable, "-m", "repo_context.cli.main", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "init-db" in result.stdout
    assert "doctor" in result.stdout
