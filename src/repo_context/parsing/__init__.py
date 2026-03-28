"""Parsing layer for repository scanning and AST extraction."""

from repo_context.parsing.ast_loader import load_file_text, parse_file
from repo_context.parsing.naming import (
    build_module_qualified_name,
    build_class_qualified_name,
    build_callable_qualified_name,
    build_module_node_id,
    build_class_node_id,
    build_callable_node_id,
    build_nested_qualified_name,
    DuplicateTracker,
)
from repo_context.parsing.ranges import (
    to_zero_based_line,
    make_position,
    make_range,
    make_name_selection_range,
)
from repo_context.parsing.docstrings import get_doc_summary
from repo_context.parsing.module_extractor import extract_module_node
from repo_context.parsing.class_extractor import extract_class_nodes
from repo_context.parsing.callable_extractor import extract_callable_nodes, extract_parameters
from repo_context.parsing.import_extractor import extract_import_edges_and_payload
from repo_context.parsing.inheritance_extractor import extract_inheritance_edges
from repo_context.parsing.pipeline import extract_file_graph
from repo_context.parsing.scope_tracker import ScopeTracker

__all__ = [
    # AST loader
    "load_file_text",
    "parse_file",
    # Naming
    "build_module_qualified_name",
    "build_class_qualified_name",
    "build_callable_qualified_name",
    "build_module_node_id",
    "build_class_node_id",
    "build_callable_node_id",
    "build_nested_qualified_name",
    "DuplicateTracker",
    # Ranges
    "to_zero_based_line",
    "make_position",
    "make_range",
    "make_name_selection_range",
    # Docstrings
    "get_doc_summary",
    # Extractors
    "extract_module_node",
    "extract_class_nodes",
    "extract_callable_nodes",
    "extract_parameters",
    "extract_import_edges_and_payload",
    "extract_inheritance_edges",
    # Pipeline
    "extract_file_graph",
    # Scope tracker
    "ScopeTracker",
]
