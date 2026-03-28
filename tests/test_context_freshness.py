"""Tests for context freshness builder."""

from repo_context.models import SymbolContext
from repo_context.context.freshness import build_freshness


def test_build_freshness_basic() -> None:
    """Test building freshness with basic context."""
    focus_node = {"last_indexed_at": "2026-01-01T00:00:00Z"}
    context = SymbolContext(
        focus_symbol={"id": "sym1"},
        incoming_edges=[{"id": "edge1"}],
        outgoing_edges=[{"id": "edge2"}],
    )
    
    freshness = build_freshness(context, focus_node)
    
    assert freshness["node_last_indexed_at"] == "2026-01-01T00:00:00Z"
    assert freshness["has_incoming_edges"] is True
    assert freshness["has_outgoing_edges"] is True
    assert freshness["context_source"] == "graph_only"


def test_build_freshness_no_edges() -> None:
    """Test building freshness with no edges."""
    focus_node = {"last_indexed_at": "2026-01-01T00:00:00Z"}
    context = SymbolContext(
        focus_symbol={"id": "sym1"},
        incoming_edges=[],
        outgoing_edges=[],
    )
    
    freshness = build_freshness(context, focus_node)
    
    assert freshness["has_incoming_edges"] is False
    assert freshness["has_outgoing_edges"] is False


def test_build_freshness_no_timestamp() -> None:
    """Test building freshness with missing timestamp."""
    focus_node = {}
    context = SymbolContext(
        focus_symbol={"id": "sym1"},
        incoming_edges=[],
        outgoing_edges=[],
    )
    
    freshness = build_freshness(context, focus_node)
    
    assert freshness["node_last_indexed_at"] is None
    assert freshness["context_source"] == "graph_only"
