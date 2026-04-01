"""Storage layer for SQLite persistence."""

from repo_context.storage.db import get_connection, close_connection
from repo_context.storage.migrations import initialize_database
from repo_context.storage.repos import upsert_repo, get_repo_by_id
from repo_context.storage.files import upsert_file, upsert_files, list_files_for_repo, delete_files_not_in_set, get_file_by_id
from repo_context.storage.nodes import (
    upsert_node,
    upsert_nodes,
    get_node_by_id,
    get_node_by_qualified_name,
    list_nodes_for_file,
    list_nodes_for_repo,
    list_child_nodes,
    list_lexical_children,
    delete_nodes_for_file,
    node_to_row,
    row_to_node,
)
from repo_context.storage.edges import (
    upsert_edge,
    upsert_edges,
    get_edge_by_id,
    list_edges_for_repo,
    list_outgoing_edges,
    list_incoming_edges,
    list_edges_for_file,
    delete_edges_for_file,
    edge_to_row,
    row_to_edge,
)
from repo_context.storage.graph import replace_file_graph
from repo_context.storage.reference_refresh import (
    upsert_reference_refresh,
    get_reference_refresh_state,
)

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
    "get_file_by_id",
    # Nodes - row mapping
    "node_to_row",
    "row_to_node",
    # Nodes - upsert
    "upsert_node",
    "upsert_nodes",
    # Nodes - read
    "get_node_by_id",
    "get_node_by_qualified_name",
    "list_nodes_for_file",
    "list_nodes_for_repo",
    "list_child_nodes",
    "list_lexical_children",
    # Nodes - delete
    "delete_nodes_for_file",
    # Edges - row mapping
    "edge_to_row",
    "row_to_edge",
    # Edges - upsert
    "upsert_edge",
    "upsert_edges",
    # Edges - read
    "get_edge_by_id",
    "list_edges_for_repo",
    "list_outgoing_edges",
    "list_incoming_edges",
    "list_edges_for_file",
    # Edges - delete
    "delete_edges_for_file",
    # Graph
    "replace_file_graph",
    # Reference refresh
    "upsert_reference_refresh",
    "get_reference_refresh_state",
]
