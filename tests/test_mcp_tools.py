"""Tests for MCP tools.

Tests cover:
- Input validation
- Tool behavior (success, not found, errors)
- Error result structure
- Ambiguous symbol handling
- Reference availability states
"""

import json
import tempfile
from pathlib import Path

import pytest

from repo_context.storage import (
    get_connection,
    close_connection,
    initialize_database,
    upsert_repo,
    upsert_files,
)
from repo_context.models.repo import RepoRecord
from repo_context.models.file import FileRecord
from repo_context.mcp.errors import (
    error_result,
    success_result,
    ERROR_INVALID_INPUT,
    ERROR_SYMBOL_NOT_FOUND,
    ERROR_AMBIGUOUS_SYMBOL,
)
from repo_context.mcp.adapters import adapt_node, adapt_edge


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
def initialized_conn(temp_db_path: Path):
    """Create an initialized database connection."""
    conn = get_connection(temp_db_path)
    initialize_database(conn)
    return conn, temp_db_path


def _create_test_graph(conn, repo_id: str = "repo:test"):
    """Create a minimal test graph."""
    import datetime
    
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    repo = RepoRecord(id=repo_id, root_path="/test", name="test", default_language="python", created_at=now)
    upsert_repo(conn, repo)

    now_str = "2024-01-01T00:00:00Z"
    file1 = FileRecord(
        id="file:src/module1.py",
        repo_id=repo_id,
        file_path="src/module1.py",
        uri="file:///test/src/module1.py",
        module_path="src.module1",
        language="python",
        content_hash="sha256:abc123",
        size_bytes=1000,
        last_modified_at=now_str,
    )
    upsert_files(conn, [file1])

    # Create symbols
    symbols = [
        {
            "id": "sym:repo:test:function:src.module1.func1",
            "repo_id": repo_id,
            "file_id": file1.id,
            "language": "python",
            "kind": "function",
            "name": "func1",
            "qualified_name": "src.module1.func1",
            "uri": "file:///test/src/module1.py",
            "range_json": json.dumps({"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 0}}),
            "selection_range_json": json.dumps({"start": {"line": 0, "character": 4}, "end": {"line": 0, "character": 9}}),
            "parent_id": "sym:repo:test:module:src.module1",
            "visibility_hint": "public",
            "doc_summary": "Test function",
            "content_hash": "sha256:abc",
            "semantic_hash": "sha256:abc",
            "source": "python-ast",
            "confidence": 1.0,
            "payload_json": json.dumps({"file_path": "src/module1.py", "module_path": "src.module1"}),
            "scope": "module",
            "lexical_parent_id": None,
            "last_indexed_at": now_str,
        },
        {
            "id": "sym:repo:test:module:src.module1",
            "repo_id": repo_id,
            "file_id": file1.id,
            "language": "python",
            "kind": "module",
            "name": "module1",
            "qualified_name": "src.module1",
            "uri": "file:///test/src/module1.py",
            "range_json": json.dumps({"start": {"line": 0, "character": 0}, "end": {"line": 100, "character": 0}}),
            "selection_range_json": json.dumps({"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}}),
            "parent_id": None,
            "visibility_hint": "public",
            "doc_summary": None,
            "content_hash": "sha256:abc123",
            "semantic_hash": "sha256:abc123",
            "source": "python-ast",
            "confidence": 1.0,
            "payload_json": json.dumps({"file_path": "src/module1.py", "module_path": "src.module1"}),
            "scope": "module",
            "lexical_parent_id": None,
            "last_indexed_at": now_str,
        },
    ]

    for symbol in symbols:
        conn.execute(
            """
            INSERT INTO nodes (
                id, repo_id, file_id, language, kind, name, qualified_name, uri,
                range_json, selection_range_json, parent_id, visibility_hint,
                doc_summary, content_hash, semantic_hash, source, confidence,
                payload_json, scope, lexical_parent_id, last_indexed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol["id"], symbol["repo_id"], symbol["file_id"], symbol["language"],
                symbol["kind"], symbol["name"], symbol["qualified_name"], symbol["uri"],
                symbol["range_json"], symbol["selection_range_json"], symbol["parent_id"],
                symbol["visibility_hint"], symbol["doc_summary"], symbol["content_hash"],
                symbol["semantic_hash"], symbol["source"], symbol["confidence"],
                symbol["payload_json"], symbol["scope"], symbol["lexical_parent_id"],
                symbol["last_indexed_at"],
            ),
        )

    conn.commit()


# ==================== Error/Success Result Tests ====================

def test_error_result_structure():
    """Test error result has required fields."""
    result = error_result("test_code", "Test message", {"key": "value"})
    assert result["ok"] is False
    assert result["error"]["code"] == "test_code"
    assert result["error"]["message"] == "Test message"
    assert result["error"]["details"] == {"key": "value"}
    assert result["data"] is None


def test_error_result_no_details():
    """Test error result without details."""
    result = error_result("test_code", "Test message")
    assert result["ok"] is False
    assert result["error"]["details"] is None


def test_success_result_structure():
    """Test success result has required fields."""
    result = success_result({"key": "value"})
    assert result["ok"] is True
    assert result["data"] == {"key": "value"}
    assert result["error"] is None


# ==================== Adapter Tests ====================

def test_adapt_node():
    """Test node adaptation."""
    node = {
        "id": "sym:test",
        "qualified_name": "test.func",
        "kind": "function",
        "scope": "module",
        "file_id": "file:test.py",
        "payload_json": json.dumps({"file_path": "test.py", "module_path": "test"}),
        "lexical_parent_id": None,
    }
    result = adapt_node(node)
    assert result["id"] == "sym:test"
    assert result["qualified_name"] == "test.func"
    assert result["kind"] == "function"
    assert result["file_path"] == "test.py"
    assert result["module_path"] == "test"


def test_adapt_edge():
    """Test edge adaptation."""
    edge = {
        "from_id": "sym:1",
        "to_id": "sym:2",
        "evidence_file_id": "file:test.py",
        "evidence_uri": "file:///test.py",
        "confidence": 0.9,
        "evidence_range_json": json.dumps({"start": {"line": 5, "character": 0}, "end": {"line": 5, "character": 10}}),
    }
    result = adapt_edge(edge)
    assert result["from_id"] == "sym:1"
    assert result["to_id"] == "sym:2"
    assert result["confidence"] == 0.9


# ==================== Schema Validation Tests ====================

def test_resolve_symbol_input_validation():
    """Test ResolveSymbolInput validation."""
    from repo_context.mcp.schemas import ResolveSymbolInput
    
    # Valid input
    inp = ResolveSymbolInput(repo_id="repo:test", qualified_name="test.func")
    assert inp.repo_id == "repo:test"
    
    # Invalid repo_id
    with pytest.raises(Exception):
        ResolveSymbolInput(repo_id="", qualified_name="test.func")
    
    # Empty qualified_name
    with pytest.raises(Exception):
        ResolveSymbolInput(repo_id="repo:test", qualified_name="")


def test_analyze_target_set_risk_input_validation():
    """Test AnalyzeTargetSetRiskInput validation."""
    from repo_context.mcp.schemas import AnalyzeTargetSetRiskInput
    
    # Valid input
    inp = AnalyzeTargetSetRiskInput(symbol_ids=["sym:1", "sym:2"])
    assert len(inp.symbol_ids) == 2
    
    # Empty list
    with pytest.raises(Exception):
        AnalyzeTargetSetRiskInput(symbol_ids=[])
    
    # Empty string in list
    with pytest.raises(Exception):
        AnalyzeTargetSetRiskInput(symbol_ids=["sym:1", ""])


# ==================== Tool Handler Tests (via direct calls) ====================

def test_resolve_symbol_success(initialized_conn):
    """Test resolve_symbol finds a symbol."""
    conn, db_path = initialized_conn
    _create_test_graph(conn)
    
    from repo_context.mcp.tools import resolve_symbol
    import asyncio
    
    result = asyncio.run(
        resolve_symbol("repo:test", "src.module1.func1", db_path=str(db_path))
    )
    data = json.loads(result)
    
    assert data["ok"] is True
    assert data["data"]["symbol"]["id"] == "sym:repo:test:function:src.module1.func1"


def test_resolve_symbol_not_found(initialized_conn):
    """Test resolve_symbol returns error for missing symbol."""
    conn, db_path = initialized_conn
    
    from repo_context.mcp.tools import resolve_symbol
    import asyncio
    
    result = asyncio.run(
        resolve_symbol("repo:test", "nonexistent.symbol", db_path=str(db_path))
    )
    data = json.loads(result)
    
    assert data["ok"] is False
    assert data["error"]["code"] == "symbol_not_found"


def test_resolve_symbol_invalid_input(initialized_conn):
    """Test resolve_symbol returns error for invalid input."""
    from repo_context.mcp.tools import resolve_symbol
    import asyncio
    
    result = asyncio.run(resolve_symbol("", ""))
    data = json.loads(result)
    
    assert data["ok"] is False
    assert data["error"]["code"] == "invalid_input"


def test_get_symbol_context_success(initialized_conn):
    """Test get_symbol_context returns context."""
    conn, db_path = initialized_conn
    _create_test_graph(conn)
    
    from repo_context.mcp.tools import get_symbol_context
    import asyncio
    
    result = asyncio.run(
        get_symbol_context("sym:repo:test:function:src.module1.func1", db_path=str(db_path))
    )
    data = json.loads(result)
    
    assert data["ok"] is True
    assert "context" in data["data"]
    assert data["data"]["context"]["focus_symbol"]["qualified_name"] == "src.module1.func1"


def test_get_symbol_context_not_found(initialized_conn):
    """Test get_symbol_context returns error for missing symbol."""
    conn, db_path = initialized_conn
    
    from repo_context.mcp.tools import get_symbol_context
    import asyncio
    
    result = asyncio.run(
        get_symbol_context("sym:nonexistent", db_path=str(db_path))
    )
    data = json.loads(result)
    
    assert data["ok"] is False
    assert data["error"]["code"] == "symbol_not_found"


def test_get_symbol_references_success(initialized_conn):
    """Test get_symbol_references returns references."""
    conn, db_path = initialized_conn
    _create_test_graph(conn)
    
    from repo_context.mcp.tools import get_symbol_references
    import asyncio
    
    result = asyncio.run(
        get_symbol_references("sym:repo:test:function:src.module1.func1", db_path=str(db_path))
    )
    data = json.loads(result)
    
    assert data["ok"] is True
    assert "references" in data["data"]
    assert "reference_summary" in data["data"]


def test_get_symbol_references_not_found(initialized_conn):
    """Test get_symbol_references returns error for missing symbol."""
    conn, db_path = initialized_conn
    
    from repo_context.mcp.tools import get_symbol_references
    import asyncio
    
    result = asyncio.run(
        get_symbol_references("sym:nonexistent", db_path=str(db_path))
    )
    data = json.loads(result)
    
    assert data["ok"] is False
    assert data["error"]["code"] == "symbol_not_found"


def test_analyze_symbol_risk_success(initialized_conn):
    """Test analyze_symbol_risk returns risk analysis."""
    conn, db_path = initialized_conn
    _create_test_graph(conn)
    
    from repo_context.mcp.tools import analyze_symbol_risk
    import asyncio
    
    result = asyncio.run(
        analyze_symbol_risk("sym:repo:test:function:src.module1.func1", db_path=str(db_path))
    )
    data = json.loads(result)
    
    assert data["ok"] is True
    assert "risk" in data["data"]
    assert "risk_score" in data["data"]["risk"]
    assert "decision" in data["data"]["risk"]
    assert "issues" in data["data"]["risk"]


def test_analyze_symbol_risk_not_found(initialized_conn):
    """Test analyze_symbol_risk returns error for missing symbol."""
    conn, db_path = initialized_conn
    
    from repo_context.mcp.tools import analyze_symbol_risk
    import asyncio
    
    result = asyncio.run(
        analyze_symbol_risk("sym:nonexistent", db_path=str(db_path))
    )
    data = json.loads(result)
    
    assert data["ok"] is False
    assert data["error"]["code"] == "symbol_not_found"


def test_analyze_target_set_risk_success(initialized_conn):
    """Test analyze_target_set_risk returns risk analysis."""
    conn, db_path = initialized_conn
    _create_test_graph(conn)
    
    from repo_context.mcp.tools import analyze_target_set_risk
    import asyncio
    
    result = asyncio.run(
        analyze_target_set_risk(["sym:repo:test:function:src.module1.func1"], db_path=str(db_path))
    )
    data = json.loads(result)
    
    assert data["ok"] is True
    assert "risk" in data["data"]


def test_analyze_target_set_risk_empty_list(initialized_conn):
    """Test analyze_target_set_risk rejects empty list."""
    from repo_context.mcp.tools import analyze_target_set_risk
    import asyncio
    
    result = asyncio.run(analyze_target_set_risk([]))
    data = json.loads(result)
    
    assert data["ok"] is False
    assert data["error"]["code"] == "invalid_input"


def test_analyze_target_set_risk_not_found(initialized_conn):
    """Test analyze_target_set_risk returns error for missing symbol."""
    conn, db_path = initialized_conn
    
    from repo_context.mcp.tools import analyze_target_set_risk
    import asyncio
    
    result = asyncio.run(
        analyze_target_set_risk(["sym:nonexistent"], db_path=str(db_path))
    )
    data = json.loads(result)
    
    assert data["ok"] is False
    assert data["error"]["code"] == "symbol_not_found"
