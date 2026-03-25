"""Storage layer for SQLite persistence."""

from repo_context.storage.db import get_connection, close_connection
from repo_context.storage.migrations import initialize_database
from repo_context.storage.repos import upsert_repo, get_repo_by_id
from repo_context.storage.files import upsert_file, upsert_files, list_files_for_repo, delete_files_not_in_set
from repo_context.storage.nodes import upsert_node, upsert_nodes, list_nodes_for_file, delete_nodes_for_file
from repo_context.storage.edges import upsert_edge, upsert_edges, list_edges_for_repo, delete_edges_for_file

__all__ = [
    # Database
    "get_connection",
    "close_connection",
    "initialize_database",
    # Repos
    "upsert_repo",
    "get_repo_by_id",
    # Files
    "upsert_file",
    "upsert_files",
    "list_files_for_repo",
    "delete_files_not_in_set",
    # Nodes
    "upsert_node",
    "upsert_nodes",
    "list_nodes_for_file",
    "delete_nodes_for_file",
    # Edges
    "upsert_edge",
    "upsert_edges",
    "list_edges_for_repo",
    "delete_edges_for_file",
]
