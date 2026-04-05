"""Indexing package for watch mode and incremental updates.

Exposes watch mode functionality for keeping the repository graph
fresh during active development.
"""

from repo_context.indexing.watch import watch_repo

__all__ = ["watch_repo"]
