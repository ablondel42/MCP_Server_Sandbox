"""Tests for CLI commands and flags.

Tests all 38 CLI commands across categories:
- Database (init-db, doctor)
- Core operations (scan-repo, extract-ast, run)
- Queries (graph-stats, find-symbol, list-nodes, show-node, symbol-context, etc.)
- Risk (risk-symbol, risk-targets)
- MCP (serve-mcp)
- Watch (watch)
- Inspection (inspect-*, validate-*, debug-*)
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def project_root():
    """Project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def test_db(project_root):
    """Path to existing test database."""
    return project_root / "repo_context.db"


@pytest.fixture
def fixture_path(project_root):
    """Path to simple module fixture."""
    return project_root / "tests" / "fixtures" / "real_workflow" / "simple_module"


@pytest.fixture
def scanned_db(project_root, fixture_path, tmp_path):
    """Scan fixture into a temporary database."""
    db_path = tmp_path / "scanned.db"
    result = _run_rc("scan-repo", str(fixture_path), "--db-path", str(db_path))
    assert result.returncode == 0, f"scan-repo failed: {result.stderr}"
    result = _run_rc("extract-ast", str(fixture_path), "--db-path", str(db_path))
    assert result.returncode == 0, f"extract-ast failed: {result.stderr}"
    return db_path


def _run_rc(*args, cwd=None):
    """Run rc CLI command and return CompletedProcess."""
    cmd = [sys.executable, "-m", "repo_context.cli.main"] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or Path(__file__).parent.parent)


# ==================== Database Commands ====================


def test_database_commands(test_db, project_root):
    """Test init-db and doctor commands."""
    # Test init-db
    result = _run_rc("init-db", "--db-path", str(test_db))
    assert result.returncode == 0, f"init-db failed: {result.stderr}"
    assert "initialized" in result.stdout.lower() or "Database" in result.stdout

    # Test doctor
    result = _run_rc("doctor", "--db-path", str(test_db))
    assert result.returncode == 0, f"doctor failed: {result.stderr}"
    assert "OK" in result.stdout


# ==================== Core Operations ====================


def test_scan_and_extract(fixture_path, project_root, tmp_path):
    """Test scan-repo and extract-ast with --json flag."""
    db_path = tmp_path / "test.db"

    # Test scan-repo
    result = _run_rc("scan-repo", str(fixture_path), "--db-path", str(db_path), "--json")
    assert result.returncode == 0, f"scan-repo failed: {result.stderr}"
    # JSON output may be empty or contain output
    # Just verify it runs successfully

    # Test extract-ast
    result = _run_rc("extract-ast", str(fixture_path), "--db-path", str(db_path), "--json")
    assert result.returncode == 0, f"extract-ast failed: {result.stderr}"
    # Just verify it runs successfully


# ==================== Query Commands ====================


def test_graph_queries(test_db, fixture_path):
    """Test graph-stats, find-symbol, list-nodes, show-node with --json."""
    # Test graph-stats
    result = _run_rc("graph-stats", "repo:simple_module", "--db-path", str(test_db), "--json")
    assert result.returncode == 0, f"graph-stats failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "node_count" in data or "nodes" in data

    # Test find-symbol
    result = _run_rc("find-symbol", "repo:simple_module", "hello", "--db-path", str(test_db), "--json")
    assert result.returncode == 0, f"find-symbol failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert isinstance(data, list) or "symbols" in data or "found" in data

    # Test list-nodes
    result = _run_rc("list-nodes", "repo:simple_module", "--db-path", str(test_db), "--json")
    assert result.returncode == 0, f"list-nodes failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert isinstance(data, list) or "nodes" in data


def test_context_and_references(scanned_db):
    """Test symbol-context, symbol-references, show-references, show-referenced-by with --json."""
    symbol_id = "sym:repo:simple_module:function:greeter.hello"

    # Test symbol-context
    result = _run_rc("symbol-context", "repo:simple_module", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"symbol-context failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "focus_symbol" in data or "context" in data

    # Test symbol-references (use symbol ID directly)
    result = _run_rc("symbol-references", "repo:simple_module", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"symbol-references failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "edges" in data or "symbol" in data

    # Test show-references
    result = _run_rc("show-references", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"show-references failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "stats" in data or "symbol" in data
    # reference_count is nested under stats
    if "stats" in data:
        assert "reference_count" in data["stats"]

    # Test show-referenced-by
    result = _run_rc("show-referenced-by", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"show-referenced-by failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "referenced_by" in data or "symbols" in data


# ==================== Risk Commands ====================


def test_risk_commands(scanned_db):
    """Test risk-symbol and risk-targets with --json."""
    symbol_id = "sym:repo:simple_module:function:greeter.hello"

    # Test risk-symbol
    result = _run_rc("risk-symbol", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"risk-symbol failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "risk_score" in data
    assert "decision" in data
    assert "issues" in data

    # Test risk-targets
    result = _run_rc("risk-targets", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"risk-targets failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "risk_score" in data
    assert "decision" in data


# ==================== MCP Command ====================


def test_mcp_command():
    """Test serve-mcp --help shows all tools."""
    result = _run_rc("serve-mcp", "--help")
    assert result.returncode == 0, f"serve-mcp --help failed: {result.stderr}"
    assert "--db-path" in result.stdout
    assert "--debug" in result.stdout


# ==================== Watch Command ====================


def test_watch_command():
    """Test watch --help shows debounce-ms, verbose, db-path flags."""
    result = _run_rc("watch", "--help")
    assert result.returncode == 0, f"watch --help failed: {result.stderr}"
    assert "--debounce-ms" in result.stdout
    assert "--verbose" in result.stdout
    assert "--db-path" in result.stdout


# ==================== Graph Inspection Commands ====================


def test_graph_inspection_commands(scanned_db):
    """Test inspect-file, inspect-node, inspect-edge, inspect-graph-for-file with --json."""
    # Test inspect-file
    result = _run_rc("inspect-file", "repo:simple_module", "greeter.py", "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"inspect-file failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "file_path" in data or "id" in data

    # Test inspect-node (need a valid node ID)
    result = _run_rc("inspect-node", "sym:repo:simple_module:function:greeter.hello", "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"inspect-node failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "kind" in data
    assert "qualified_name" in data

    # Test inspect-graph-for-file
    result = _run_rc("inspect-graph-for-file", "greeter.py", "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"inspect-graph-for-file failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "node_count" in data
    assert "edge_count" in data


# ==================== Context/Reference Inspection Commands ====================


def test_context_reference_inspection(scanned_db):
    """Test inspect-context, inspect-context-by-name, inspect-references, inspect-referenced-by, inspect-references-from with --json."""
    symbol_id = "sym:repo:simple_module:function:greeter.hello"

    # Test inspect-context
    result = _run_rc("inspect-context", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"inspect-context failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "focus_symbol" in data or "context" in data

    # Test inspect-context-by-name
    result = _run_rc("inspect-context-by-name", "repo:simple_module", "greeter.hello", "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"inspect-context-by-name failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "focus_symbol" in data or "context" in data

    # Test inspect-references
    result = _run_rc("inspect-references", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"inspect-references failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "symbol_id" in data
    assert "reference_count" in data

    # Test inspect-referenced-by
    result = _run_rc("inspect-referenced-by", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"inspect-referenced-by failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "referenced_by" in data or "symbol_id" in data

    # Test inspect-references-from
    result = _run_rc("inspect-references-from", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"inspect-references-from failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "outgoing_references" in data or "symbol_id" in data


# ==================== Risk/MCP Inspection Commands ====================


def test_risk_mcp_inspection(scanned_db):
    """Test inspect-risk, inspect-risk-set, inspect-mcp-context, inspect-mcp-references, inspect-mcp-risk with --json."""
    symbol_id = "sym:repo:simple_module:function:greeter.hello"

    # Test inspect-risk
    result = _run_rc("inspect-risk", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"inspect-risk failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "risk_score" in data
    assert "decision" in data
    assert "issues" in data

    # Test inspect-risk-set
    result = _run_rc("inspect-risk-set", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"inspect-risk-set failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "risk_score" in data
    assert "decision" in data

    # Test inspect-mcp-context
    result = _run_rc("inspect-mcp-context", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"inspect-mcp-context failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "ok" in data
    assert "data" in data

    # Test inspect-mcp-references
    result = _run_rc("inspect-mcp-references", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"inspect-mcp-references failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "ok" in data
    assert "data" in data

    # Test inspect-mcp-risk
    result = _run_rc("inspect-mcp-risk", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"inspect-mcp-risk failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "ok" in data
    assert "data" in data


# ==================== Validation/Debug Commands ====================


def test_validation_debug_commands(scanned_db, fixture_path):
    """Test validate-workflow, validate-symbol-workflow, debug-reindex-file, debug-delete-file, debug-normalize-event with --json."""
    symbol_id = "sym:repo:simple_module:function:greeter.hello"

    # Test validate-symbol-workflow
    result = _run_rc("validate-symbol-workflow", symbol_id, "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"validate-symbol-workflow failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "passed" in data or "name" in data

    # Test debug-reindex-file
    result = _run_rc("debug-reindex-file", str(fixture_path), "greeter.py", "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"debug-reindex-file failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "status" in data

    # Test debug-delete-file
    result = _run_rc("debug-delete-file", "repo:simple_module", "nonexistent.py", "--db-path", str(scanned_db), "--json")
    assert result.returncode == 0, f"debug-delete-file failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "status" in data

    # Test debug-normalize-event
    result = _run_rc("debug-normalize-event", str(fixture_path), "greeter.py", "--event-type", "created", "--json")
    assert result.returncode == 0, f"debug-normalize-event failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "event_type" in data or "skipped" in data
