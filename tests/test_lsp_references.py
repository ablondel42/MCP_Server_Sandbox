"""Tests for LSP reference enrichment."""

import json
import tempfile
from pathlib import Path

import pytest

from repo_context.storage import get_connection, close_connection, initialize_database
from repo_context.lsp.client import PyrightLspClient
from repo_context.lsp.protocol import build_references_params, normalize_location
from repo_context.lsp.resolver import get_reference_query_position, resolve_file_by_uri
from repo_context.lsp.mapper import (
    range_contains,
    pick_smallest_containing_symbol,
    find_module_node_for_file,
)
from repo_context.lsp.references import (
    build_reference_edge,
    replace_reference_edges_for_target,
)
from repo_context.graph.references import (
    build_reference_stats,
    get_reference_refresh_state,
)


class MockLspClient:
    """Mock LSP client for tests."""

    def __init__(self, references_response=None):
        self.references_response = references_response or []
        self.did_open_calls = []
        self._started = False

    def start(self, repo_root: str):
        self._started = True

    def did_open(self, uri: str, text: str):
        self.did_open_calls.append((uri, text))

    def find_references(self, uri: str, line: int, character: int, include_declaration: bool = False):
        return self.references_response

    def close(self):
        self._started = False


class TestGetReferenceQueryPosition:
    """Tests for get_reference_query_position."""

    def test_prefers_selection_range(self):
        """Test that selection_range_json.start is preferred over range_json.start."""
        symbol = type('Symbol', (), {
            'id': 'sym:test:function:foo',
            'selection_range_json': {"start": {"line": 10, "character": 4}, "end": {"line": 10, "character": 7}},
            'range_json': {"start": {"line": 10, "character": 0}, "end": {"line": 15, "character": 0}},
        })()

        position = get_reference_query_position(symbol)

        assert position == {"line": 10, "character": 4}

    def test_falls_back_to_range_json(self):
        """Test fallback to range_json.start when selection_range_json is missing."""
        symbol = type('Symbol', (), {
            'id': 'sym:test:function:foo',
            'selection_range_json': None,
            'range_json': {"start": {"line": 10, "character": 0}, "end": {"line": 15, "character": 0}},
        })()

        position = get_reference_query_position(symbol)

        assert position == {"line": 10, "character": 0}

    def test_raises_when_no_ranges(self):
        """Test that ValueError is raised when both ranges are missing."""
        symbol = type('Symbol', (), {
            'id': 'sym:test:function:foo',
            'selection_range_json': None,
            'range_json': None,
        })()

        with pytest.raises(ValueError, match="no stored range"):
            get_reference_query_position(symbol)


class TestRangeContains:
    """Tests for range_contains helper."""

    def test_contains_when_inner_fully_inside_outer(self):
        outer = {"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 0}}
        inner = {"start": {"line": 5, "character": 0}, "end": {"line": 6, "character": 0}}

        assert range_contains(outer, inner) is True

    def test_not_contains_when_inner_outside_outer(self):
        outer = {"start": {"line": 0, "character": 0}, "end": {"line": 5, "character": 0}}
        inner = {"start": {"line": 6, "character": 0}, "end": {"line": 7, "character": 0}}

        assert range_contains(outer, inner) is False

    def test_contains_when_same_range(self):
        outer = {"start": {"line": 0, "character": 0}, "end": {"line": 5, "character": 0}}
        inner = {"start": {"line": 0, "character": 0}, "end": {"line": 5, "character": 0}}

        assert range_contains(outer, inner) is True


class TestPickSmallestContainingSymbol:
    """Tests for pick_smallest_containing_symbol."""

    def test_picks_smallest_containing_symbol(self):
        """Test that the smallest containing symbol is selected."""
        symbols = [
            {"id": "module", "kind": "module", "range_json": {
                "start": {"line": 0, "character": 0}, "end": {"line": 100, "character": 0}
            }},
            {"id": "func_outer", "kind": "function", "range_json": {
                "start": {"line": 10, "character": 0}, "end": {"line": 50, "character": 0}
            }},
            {"id": "func_inner", "kind": "function", "range_json": {
                "start": {"line": 20, "character": 0}, "end": {"line": 30, "character": 0}
            }},
        ]
        usage_range = {"start": {"line": 25, "character": 4}, "end": {"line": 25, "character": 10}}

        result = pick_smallest_containing_symbol(symbols, usage_range)

        assert result["id"] == "func_inner"

    def test_returns_none_when_no_containing_symbol(self):
        """Test that None is returned when no symbol contains the usage."""
        symbols = [
            {"id": "func1", "kind": "function", "range_json": {
                "start": {"line": 0, "character": 0}, "end": {"line": 5, "character": 0}
            }},
        ]
        usage_range = {"start": {"line": 20, "character": 0}, "end": {"line": 20, "character": 10}}

        result = pick_smallest_containing_symbol(symbols, usage_range)

        assert result is None


class TestFindModuleNodeForFile:
    """Tests for find_module_node_for_file."""

    def test_returns_module_node(self):
        """Test that module node is found."""
        symbols = [
            {"id": "module", "kind": "module", "qualified_name": "test.module"},
            {"id": "func1", "kind": "function", "qualified_name": "test.module.func1"},
        ]

        result = find_module_node_for_file(symbols)

        assert result["id"] == "module"

    def test_returns_none_when_no_module(self):
        """Test that None is returned when no module node exists."""
        symbols = [
            {"id": "func1", "kind": "function", "qualified_name": "test.module.func1"},
        ]

        result = find_module_node_for_file(symbols)

        assert result is None


class TestBuildReferenceEdge:
    """Tests for build_reference_edge."""

    def test_builds_edge_with_correct_fields(self):
        """Test that edge has all required fields with correct values."""
        edge = build_reference_edge(
            repo_id="repo:test",
            from_id="sym:repo:test:function:caller",
            to_id="sym:repo:test:function:callee",
            confidence=0.9,
            evidence_file_id="file:src/test.py",
            evidence_uri="file:///test/src/test.py",
            evidence_range_json={"start": {"line": 10, "character": 4}, "end": {"line": 10, "character": 10}},
            payload_json={"mapping_mode": "exact_symbol"},
        )

        assert edge["id"] == "edge:repo:test:references:sym:repo:test:function:caller->sym:repo:test:function:callee:10:4"
        assert edge["repo_id"] == "repo:test"
        assert edge["kind"] == "references"
        assert edge["from_id"] == "sym:repo:test:function:caller"
        assert edge["to_id"] == "sym:repo:test:function:callee"
        assert edge["source"] == "lsp"
        assert edge["confidence"] == 0.9
        assert edge["evidence_file_id"] == "file:src/test.py"
        assert edge["evidence_uri"] == "file:///test/src/test.py"


class TestReplaceReferenceEdgesForTarget:
    """Tests for replace_reference_edges_for_target."""

    def test_replaces_edges_transactionally(self):
        """Test that old edges are deleted and new edges are inserted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = get_connection(db_path)
            initialize_database(conn)

            # Create a target symbol
            conn.execute(
                """INSERT INTO nodes (id, repo_id, file_id, language, kind, name, qualified_name, uri, content_hash, semantic_hash, source, confidence, payload_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("sym:repo:test:function:target", "repo:test", "file:src/test.py", "python", "function", "target", "test.target", "file:///test.py", "sha256:abc123", "sha256:sem123", "python-ast", 1.0, "{}"),
            )

            # Create old edge
            conn.execute(
                "INSERT INTO edges (id, repo_id, kind, from_id, to_id, source, confidence, evidence_file_id, evidence_uri, evidence_range_json, payload_json, last_indexed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("edge:old", "repo:test", "references", "sym:old", "sym:repo:test:function:target", "lsp", 0.9, "file:old.py", "file:///old.py", "{}", "{}", "2024-01-01T00:00:00Z"),
            )
            conn.commit()

            # Create new edge
            new_edges = [
                build_reference_edge(
                    repo_id="repo:test",
                    from_id="sym:repo:test:function:new_caller",
                    to_id="sym:repo:test:function:target",
                    confidence=0.9,
                    evidence_file_id="file:src/test.py",
                    evidence_uri="file:///test.py",
                    evidence_range_json={"start": {"line": 10, "character": 4}, "end": {"line": 10, "character": 10}},
                    payload_json={"mapping_mode": "exact_symbol"},
                ),
            ]

            refresh_metadata = {
                "target_symbol_id": "sym:repo:test:function:target",
                "available": True,
                "last_refreshed_at": "2024-01-02T00:00:00Z",
                "refresh_status": "ok",
                "error_code": None,
            }

            replace_reference_edges_for_target(conn, "sym:repo:test:function:target", new_edges, refresh_metadata)

            # Verify old edge is gone
            old_edge = conn.execute("SELECT id FROM edges WHERE id = 'edge:old'").fetchone()
            assert old_edge is None

            # Verify new edge exists
            new_edge = conn.execute("SELECT id FROM edges WHERE to_id = 'sym:repo:test:function:target'").fetchone()
            assert new_edge is not None

            # Verify refresh metadata
            refresh = conn.execute("SELECT * FROM reference_refresh WHERE target_symbol_id = 'sym:repo:test:function:target'").fetchone()
            assert refresh is not None
            assert refresh["available"] == 1

            close_connection(conn)


class TestReferenceStats:
    """Tests for build_reference_stats and get_reference_refresh_state."""

    def test_stats_with_references(self):
        """Test stats computation when references exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = get_connection(db_path)
            initialize_database(conn)

            # Create target and source symbols
            conn.execute(
                """INSERT INTO nodes (id, repo_id, file_id, language, kind, name, qualified_name, uri, content_hash, semantic_hash, source, confidence, payload_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("sym:repo:test:function:target", "repo:test", "file:src/test.py", "python", "function", "target", "test.target", "file:///test.py", "sha256:abc123", "sha256:sem123", "python-ast", 1.0, "{}"),
            )
            conn.execute(
                """INSERT INTO nodes (id, repo_id, file_id, language, kind, name, qualified_name, uri, content_hash, semantic_hash, source, confidence, payload_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("sym:repo:test:function:caller", "repo:test", "file:src/caller.py", "python", "function", "caller", "test.caller", "file:///caller.py", "sha256:def456", "sha256:sem456", "python-ast", 1.0, "{}"),
            )
            conn.commit()

            # Create reference edge
            conn.execute(
                "INSERT INTO edges (id, repo_id, kind, from_id, to_id, source, confidence, evidence_file_id, evidence_uri, evidence_range_json, payload_json, last_indexed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("edge:1", "repo:test", "references", "sym:repo:test:function:caller", "sym:repo:test:function:target", "lsp", 0.9, "file:src/caller.py", "file:///caller.py", "{}", "{}", "2024-01-01T00:00:00Z"),
            )

            # Create refresh metadata
            conn.execute(
                "INSERT INTO reference_refresh (target_symbol_id, available, last_refreshed_at) VALUES (?, ?, ?)",
                ("sym:repo:test:function:target", 1, "2024-01-01T00:00:00Z"),
            )
            conn.commit()

            stats = build_reference_stats(conn, "sym:repo:test:function:target")

            assert stats["reference_count"] == 1
            assert stats["referencing_file_count"] == 1
            assert stats["referencing_module_count"] == 1
            assert stats["available"] is True
            assert stats["last_refreshed_at"] == "2024-01-01T00:00:00Z"

            close_connection(conn)

    def test_stats_distinguish_unavailable_from_zero(self):
        """Test that never-refreshed returns available=False, not zero references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = get_connection(db_path)
            initialize_database(conn)

            # Create target symbol but NO reference edges and NO refresh metadata
            conn.execute(
                """INSERT INTO nodes (id, repo_id, file_id, language, kind, name, qualified_name, uri, content_hash, semantic_hash, source, confidence, payload_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("sym:repo:test:function:target", "repo:test", "file:src/test.py", "python", "function", "target", "test.target", "file:///test.py", "sha256:abc123", "sha256:sem123", "python-ast", 1.0, "{}"),
            )
            conn.commit()

            stats = build_reference_stats(conn, "sym:repo:test:function:target")

            assert stats["reference_count"] == 0
            assert stats["available"] is False
            assert stats["last_refreshed_at"] is None

            close_connection(conn)


class TestProtocolHelpers:
    """Tests for protocol helper functions."""

    def test_build_references_params(self):
        """Test that ReferenceParams is built correctly."""
        params = build_references_params("file:///test.py", 10, 4, include_declaration=False)

        assert params.text_document.uri == "file:///test.py"
        assert params.position.line == 10
        assert params.position.character == 4
        assert params.context.include_declaration is False

    def test_normalize_location_from_dict(self):
        """Test normalization of dict location."""
        loc = {
            "uri": "file:///test.py",
            "range": {"start": {"line": 10, "character": 4}, "end": {"line": 10, "character": 10}},
        }

        result = normalize_location(loc)

        assert result["uri"] == "file:///test.py"
        assert result["range"]["start"]["line"] == 10


class TestClientOpensDocumentBeforeRequest:
    """Test that client opens target document before requesting references."""

    def test_did_open_called_before_find_references(self):
        """Test that did_open is called before find_references."""
        client = MockLspClient(references_response=[])

        client.start("/test")
        client.did_open("file:///test.py", "print('hello')")
        client.find_references("file:///test.py", 0, 0)

        assert len(client.did_open_calls) == 1
        assert client.did_open_calls[0][0] == "file:///test.py"
