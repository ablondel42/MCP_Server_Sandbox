"""Tests for context summary builders."""

from repo_context.models import SymbolContext
from repo_context.context.summaries import (
    build_structural_summary,
    build_confidence,
    _is_local_declaration,
)


def test_build_structural_summary_basic() -> None:
    """Test building structural summary with basic context."""
    context = SymbolContext(
        focus_symbol={"id": "sym1", "kind": "function", "scope": "module"},
        structural_parent={"id": "parent1"},
        structural_children=[{"id": "child1"}, {"id": "child2"}],
        lexical_parent=None,
        lexical_children=[],
        incoming_edges=[{"id": "edge1"}],
        outgoing_edges=[{"id": "edge2"}, {"id": "edge3"}],
        file_siblings=[{"id": "sib1"}],
    )
    
    summary = build_structural_summary(context)
    
    assert summary["has_structural_parent"] is True
    assert summary["structural_child_count"] == 2
    assert summary["has_lexical_parent"] is False
    assert summary["lexical_child_count"] == 0
    assert summary["incoming_edge_count"] == 1
    assert summary["outgoing_edge_count"] == 2
    assert summary["same_file_sibling_count"] == 1
    assert summary["scope"] == "module"
    assert summary["is_local_declaration"] is False
    assert summary["is_nested_declaration"] is False


def test_build_structural_summary_local_function() -> None:
    """Test structural summary for local function."""
    context = SymbolContext(
        focus_symbol={"id": "sym1", "kind": "local_function", "scope": "function", "lexical_parent_id": "parent1"},
        structural_parent=None,
        structural_children=[],
        lexical_parent={"id": "parent1"},
        lexical_children=[],
        incoming_edges=[],
        outgoing_edges=[],
        file_siblings=[],
    )
    
    summary = build_structural_summary(context)
    
    assert summary["is_local_declaration"] is True
    assert summary["is_nested_declaration"] is True
    assert summary["scope"] == "function"


def test_build_structural_summary_local_class() -> None:
    """Test structural summary for local class."""
    context = SymbolContext(
        focus_symbol={"id": "sym1", "kind": "class", "scope": "function", "lexical_parent_id": "parent1"},
        structural_parent=None,
        structural_children=[],
        lexical_parent={"id": "parent1"},
        lexical_children=[],
        incoming_edges=[],
        outgoing_edges=[],
        file_siblings=[],
    )
    
    summary = build_structural_summary(context)
    
    assert summary["is_local_declaration"] is True
    assert summary["is_nested_declaration"] is True


def test_build_confidence_basic() -> None:
    """Test building confidence with basic context."""
    context = SymbolContext(
        focus_symbol={"id": "sym1", "confidence": 0.9},
        incoming_edges=[{"confidence": 0.8}],
        outgoing_edges=[{"confidence": 1.0}],
    )
    
    confidence = build_confidence(context)
    
    assert confidence["focus_symbol_confidence"] == 0.9
    assert confidence["edge_confidence_min"] == 0.8
    assert confidence["edge_confidence_max"] == 1.0
    assert confidence["graph_only"] is True


def test_build_confidence_no_edges() -> None:
    """Test building confidence with no edges."""
    context = SymbolContext(
        focus_symbol={"id": "sym1", "confidence": 1.0},
        incoming_edges=[],
        outgoing_edges=[],
    )
    
    confidence = build_confidence(context)
    
    assert confidence["focus_symbol_confidence"] == 1.0
    assert confidence["edge_confidence_min"] == 1.0
    assert confidence["edge_confidence_max"] == 1.0


def test_build_confidence_with_placeholder_targets() -> None:
    """Test confidence reports placeholder targets."""
    context = SymbolContext(
        focus_symbol={"id": "sym1", "confidence": 1.0},
        incoming_edges=[{"from_id": "sym1", "to_id": "external_or_unresolved:ext"}],
        outgoing_edges=[],
    )
    
    confidence = build_confidence(context)
    
    assert confidence["contains_placeholder_targets"] is True


def test_is_local_declaration_function() -> None:
    """Test _is_local_declaration for various function types."""
    # Module-level function
    assert _is_local_declaration({"kind": "function", "scope": "module"}) is False
    assert _is_local_declaration({"kind": "async_function", "scope": "module"}) is False
    
    # Local function
    assert _is_local_declaration({"kind": "local_function", "scope": "function"}) is True
    assert _is_local_declaration({"kind": "local_async_function", "scope": "function"}) is True


def test_is_local_declaration_class() -> None:
    """Test _is_local_declaration for class types."""
    # Module-level class
    assert _is_local_declaration({"kind": "class", "scope": "module"}) is False
    
    # Local class
    assert _is_local_declaration({"kind": "class", "scope": "function"}) is True


def test_is_local_declaration_method() -> None:
    """Test _is_local_declaration for method types."""
    # Methods are not local declarations
    assert _is_local_declaration({"kind": "method", "scope": "class"}) is False
    assert _is_local_declaration({"kind": "async_method", "scope": "class"}) is False
