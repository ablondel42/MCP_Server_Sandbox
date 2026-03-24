"""Application configuration."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    """Application configuration."""

    app_name: str = "repo-context-mcp"
    db_path: Path = Path("repo_context.db")
    debug: bool = False
    ignored_dirs: tuple[str, ...] = (
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "build",
        "dist",
        "node_modules",
    )
    supported_extensions: tuple[str, ...] = (".py",)


def get_config() -> AppConfig:
    """Get the application configuration."""
    return AppConfig()
