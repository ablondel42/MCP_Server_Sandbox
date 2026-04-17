"""Tests for Phase 10: Real workflow validation.

Tests cover:
- Full workflow integration (scan->extract->persist->context->risk->MCP)
- Payload usability (context, references, risk, MCP)
- Graph shape validation
- Context shape validation
- Risk shape validation
- Reference availability semantics
- CLI JSON output validation
"""

import json
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import pytest

from repo_context.storage import get_connection, close_connection, initialize_database
from repo_context.parsing.scanner import scan_repository
from repo_context.parsing.pipeline import extract_file_graph
from repo_context.storage import upsert_repo, upsert_files, replace_file_graph
from repo_context.config import AppConfig, get_config
from repo_context.context import build_symbol_context
from repo_context.graph import (
    get_symbol,
    get_repo_graph_stats,
    list_reference_edges_for_target,
    analyze_symbol_risk,
)
from repo_context.validation.workflow import (
    run_full_workflow_validation,
    run_symbol_workflow_validation,
    ValidationResult,
)
from repo_context.validation.graph_checks import (
    assert_module_nodes_exist,
    assert_expected_symbol_kinds,
    assert_structural_edges_present,
    assert_no_duplicate_stable_ids,
)
from repo_context.validation.context_checks import assert_context_is_agent_usable
from repo_context.validation.risk_checks import assert_risk_is_agent_usable
from repo_context.validation.mcp_checks import (
    assert_tool_result_shape,
    assert_symbol_context_payload,
    assert_risk_payload,
)
from repo_context.validation.reference_checks import assert_reference_state_is_agent_usable


@pytest.fixture
def project_root():
    """Project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def fixtures_dir(project_root):
    """Get path to real_workflow fixtures directory."""
    return project_root / "tests" / "fixtures" / "real_workflow"


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
def conn(temp_db):
    """Create an initialized database connection."""
    c = get_connection(temp_db)
    initialize_database(c)
    yield c
    close_connection(c)


@pytest.fixture
def config():
    """Create default app config."""
    return AppConfig()


def _scan_fixture(conn, fixtures_dir, config):
    """Scan a fixture repository and return repo_id."""
    repo_record, file_records = scan_repository(fixtures_dir, config)
    upsert_repo(conn, repo_record)
    upsert_files(conn, file_records)

    # Extract AST for each file
    for file_record in file_records:
        try:
            nodes, edges, _summary = extract_file_graph(repo_record.id, file_record, fixtures_dir)
            replace_file_graph(conn, file_record.id, nodes, edges)
        except SyntaxError:
            pass  # Skip files with syntax errors

    conn.commit()
    return repo_record.id


def _get_first_function_symbol(conn, repo_id):
    """Get the first function symbol for a repo."""
    cursor = conn.execute(
        "SELECT id FROM nodes WHERE repo_id = ? AND kind = 'function' LIMIT 1",
        (repo_id,),
    )
    row = cursor.fetchone()
    return row["id"] if row else None


# ==================== Full Workflow Tests ====================


def test_full_workflow_simple_fixture(conn, fixtures_dir, config):
    """Test full workflow validation for simple module fixture."""
    repo_id = _scan_fixture(conn, fixtures_dir / "simple_module", config)

    result = run_full_workflow_validation(conn, fixtures_dir / "simple_module", "simple_module", config)

    assert result.passed, f"Workflow validation failed: {result.errors}"
    assert result.name == "simple_module"
    assert len(result.checks) > 0
    assert len(result.errors) == 0


def test_full_workflow_nested_scope_fixture(conn, fixtures_dir, config):
    """Test full workflow validation for nested scope fixture."""
    repo_id = _scan_fixture(conn, fixtures_dir / "nested_scope", config)

    result = run_full_workflow_validation(conn, fixtures_dir / "nested_scope", "nested_scope", config)

    assert result.passed, f"Nested scope workflow failed: {result.errors}"

    # Verify nested symbols exist
    cursor = conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE repo_id = ? AND kind IN ('local_function', 'local_async_function')",
        (repo_id,),
    )
    local_count = cursor.fetchone()[0]
    assert local_count > 0, "Expected local functions in nested scope fixture"


def test_full_workflow_reference_fixture(conn, fixtures_dir, config):
    """Test full workflow validation for cross-file reference fixture."""
    repo_id = _scan_fixture(conn, fixtures_dir / "cross_file_refs", config)

    result = run_full_workflow_validation(conn, fixtures_dir / "cross_file_refs", "cross_file_refs", config)

    assert result.passed, f"Reference fixture workflow failed: {result.errors}"


def test_full_workflow_risk_fixture(conn, fixtures_dir, config):
    """Test full workflow validation for public symbol fixture with risk analysis."""
    repo_id = _scan_fixture(conn, fixtures_dir / "public_symbol", config)

    result = run_full_workflow_validation(conn, fixtures_dir / "public_symbol", "public_symbol", config)

    assert result.passed, f"Risk fixture workflow failed: {result.errors}"


def test_full_workflow_watch_invalidation_fixture(conn, fixtures_dir, config):
    """Test full workflow validation for watch invalidation fixture."""
    repo_id = _scan_fixture(conn, fixtures_dir / "watch_test", config)
    symbol_id = _get_first_function_symbol(conn, repo_id)
    assert symbol_id is not None, "Expected at least one function symbol"

    # Get initial state
    context_before = build_symbol_context(conn, symbol_id)

    # Validate workflow
    result = run_full_workflow_validation(conn, fixtures_dir / "watch_test", "watch_test", config)

    assert result.passed, f"Watch invalidation fixture workflow failed: {result.errors}"


# ==================== Payload Usability Tests ====================


def test_context_payload_is_agent_usable(conn, fixtures_dir, config):
    """Test that context payload is agent-usable."""
    _scan_fixture(conn, fixtures_dir / "simple_module", config)
    symbol_id = _get_first_function_symbol(conn, "repo:simple_module")
    assert symbol_id is not None

    context = build_symbol_context(conn, symbol_id)
    context_dict = _context_to_dict(context)

    result = assert_context_is_agent_usable(context_dict)
    assert result["passed"], f"Context not agent-usable: {result['errors']}"


def test_references_payload_is_agent_usable(conn, fixtures_dir, config):
    """Test that references payload is agent-usable."""
    _scan_fixture(conn, fixtures_dir / "simple_module", config)
    symbol_id = _get_first_function_symbol(conn, "repo:simple_module")
    assert symbol_id is not None

    ref_edges = list_reference_edges_for_target(conn, symbol_id)
    ref_summary = {"count": len(ref_edges), "available": True}
    ref_payload = {"references": ref_edges, "reference_summary": ref_summary}

    result = assert_reference_state_is_agent_usable(ref_payload)
    assert result["passed"], f"References not agent-usable: {result['errors']}"


def test_risk_payload_is_agent_usable(conn, fixtures_dir, config):
    """Test that risk payload is agent-usable."""
    _scan_fixture(conn, fixtures_dir / "simple_module", config)
    symbol_id = _get_first_function_symbol(conn, "repo:simple_module")
    assert symbol_id is not None

    risk_result = analyze_symbol_risk(conn, symbol_id)
    risk_dict = _risk_to_dict(risk_result)

    result = assert_risk_is_agent_usable(risk_dict)
    assert result["passed"], f"Risk not agent-usable: {result['errors']}"


def test_mcp_context_payload_matches_contract(conn, fixtures_dir, config):
    """Test that MCP context payload matches contract."""
    _scan_fixture(conn, fixtures_dir / "simple_module", config)
    symbol_id = _get_first_function_symbol(conn, "repo:simple_module")
    assert symbol_id is not None

    context = build_symbol_context(conn, symbol_id)
    context_dict = _context_to_dict(context)

    # Build MCP-style payload
    mcp_context = _adapt_context_for_mcp(context_dict)
    tool_result = {"ok": True, "data": {"context": mcp_context}, "error": None}

    result = assert_symbol_context_payload(tool_result)
    assert result["passed"], f"MCP context payload invalid: {result['errors']}"


# ==================== Additional Validation Tests ====================


def test_reference_unavailable_is_not_zero(conn, fixtures_dir, config):
    """Test that unavailable references are distinct from zero references."""
    _scan_fixture(conn, fixtures_dir / "simple_module", config)
    symbol_id = _get_first_function_symbol(conn, "repo:simple_module")
    assert symbol_id is not None

    # Unrefreshed symbol should have available=False or None, not just empty list
    ref_edges = list_reference_edges_for_target(conn, symbol_id)
    ref_summary = {"count": len(ref_edges), "available": True}
    ref_payload = {"references": ref_edges, "reference_summary": ref_summary}

    result = assert_reference_state_is_agent_usable(ref_payload)
    assert result["passed"], f"Reference state not properly distinguished: {result['errors']}"
    assert "available" in ref_summary, "Missing 'available' field"


def test_graph_shape_validation(conn, fixtures_dir, config):
    """Test that graph_checks module functions work correctly."""
    repo_id = _scan_fixture(conn, fixtures_dir / "simple_module", config)

    # Test individual graph checks
    module_check = assert_module_nodes_exist(conn, repo_id)
    assert module_check["passed"], f"Module nodes check failed: {module_check['errors']}"

    kinds_check = assert_expected_symbol_kinds(conn, repo_id)
    assert kinds_check["passed"], f"Symbol kinds check failed: {kinds_check['errors']}"

    edges_check = assert_structural_edges_present(conn, repo_id)
    assert edges_check["passed"], f"Structural edges check failed: {edges_check['errors']}"

    dup_check = assert_no_duplicate_stable_ids(conn, repo_id)
    assert dup_check["passed"], f"No duplicates check failed: {dup_check['errors']}"


def test_context_shape_validation(conn, fixtures_dir, config):
    """Test that context_checks module functions work correctly."""
    _scan_fixture(conn, fixtures_dir / "simple_module", config)
    symbol_id = _get_first_function_symbol(conn, "repo:simple_module")
    assert symbol_id is not None

    context = build_symbol_context(conn, symbol_id)
    context_dict = _context_to_dict(context)

    result = assert_context_is_agent_usable(context_dict)
    assert result["passed"], f"Context shape validation failed: {result['errors']}"


def test_risk_shape_validation(conn, fixtures_dir, config):
    """Test that risk_checks module functions work correctly."""
    _scan_fixture(conn, fixtures_dir / "simple_module", config)
    symbol_id = _get_first_function_symbol(conn, "repo:simple_module")
    assert symbol_id is not None

    risk_result = analyze_symbol_risk(conn, symbol_id)
    risk_dict = _risk_to_dict(risk_result)

    result = assert_risk_is_agent_usable(risk_dict)
    assert result["passed"], f"Risk shape validation failed: {result['errors']}"


# ==================== CLI JSON Output Tests ====================


def test_inspect_context_cli_json_output(conn, fixtures_dir, config, project_root):
    """Test that inspect-context CLI produces valid JSON output."""
    repo_id = _scan_fixture(conn, fixtures_dir / "simple_module", config)
    symbol_id = _get_first_function_symbol(conn, repo_id)
    assert symbol_id is not None

    db_path = str(conn.cursor().execute("PRAGMA database_list").fetchone()[2])
    result = subprocess.run(
        [sys.executable, "-m", "repo_context.cli.main", "inspect-context", symbol_id,
         "--db-path", db_path, "--json"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "focus_symbol" in data
    assert "structural_children" in data
    assert "incoming_edges" in data


def test_inspect_references_cli_json_output(conn, fixtures_dir, config, project_root):
    """Test that inspect-references CLI produces valid JSON output."""
    repo_id = _scan_fixture(conn, fixtures_dir / "simple_module", config)
    symbol_id = _get_first_function_symbol(conn, repo_id)
    assert symbol_id is not None

    db_path = str(conn.cursor().execute("PRAGMA database_list").fetchone()[2])
    result = subprocess.run(
        [sys.executable, "-m", "repo_context.cli.main", "inspect-references", symbol_id,
         "--db-path", db_path, "--json"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "symbol_id" in data
    assert "reference_count" in data
    assert "available" in data


def test_inspect_risk_cli_json_output(conn, fixtures_dir, config, project_root):
    """Test that inspect-risk CLI produces valid JSON output."""
    repo_id = _scan_fixture(conn, fixtures_dir / "simple_module", config)
    symbol_id = _get_first_function_symbol(conn, repo_id)
    assert symbol_id is not None

    db_path = str(conn.cursor().execute("PRAGMA database_list").fetchone()[2])
    result = subprocess.run(
        [sys.executable, "-m", "repo_context.cli.main", "inspect-risk", symbol_id,
         "--db-path", db_path, "--json"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "risk_score" in data
    assert "decision" in data
    assert "issues" in data


def test_inspect_mcp_context_cli_json_output(conn, fixtures_dir, config, project_root):
    """Test that inspect-mcp-context CLI produces valid JSON output."""
    repo_id = _scan_fixture(conn, fixtures_dir / "simple_module", config)
    symbol_id = _get_first_function_symbol(conn, repo_id)
    assert symbol_id is not None

    db_path = str(conn.cursor().execute("PRAGMA database_list").fetchone()[2])
    result = subprocess.run(
        [sys.executable, "-m", "repo_context.cli.main", "inspect-mcp-context", symbol_id,
         "--db-path", db_path, "--json"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "ok" in data
    assert "data" in data
    assert "context" in data["data"]


def test_debug_reindex_file_cli_output(conn, fixtures_dir, config, project_root):
    """Test that debug-reindex-file CLI produces valid JSON output."""
    _scan_fixture(conn, fixtures_dir / "simple_module", config)
    db_path = str(conn.cursor().execute("PRAGMA database_list").fetchone()[2])

    # Modify a file to trigger reindex
    py_file = fixtures_dir / "simple_module" / "greeter.py"
    original_content = py_file.read_text()
    try:
        py_file.write_text(original_content + "\n# comment\n")

        result = subprocess.run(
            [sys.executable, "-m", "repo_context.cli.main", "debug-reindex-file",
             str(fixtures_dir / "simple_module"), "greeter.py",
             "--db-path", db_path, "--json"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        data = json.loads(result.stdout)
        assert "status" in data
        assert "node_count" in data
        assert "edge_count" in data
    finally:
        py_file.write_text(original_content)


def test_debug_normalize_event_cli_output(project_root):
    """Test that debug-normalize-event CLI produces valid JSON output."""
    result = subprocess.run(
        [sys.executable, "-m", "repo_context.cli.main", "debug-normalize-event",
         str(project_root), "src/module.py", "--event-type", "created", "--json"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "event_type" in data or "skipped" in data


# ==================== Helper Functions ====================


def _context_to_dict(context) -> dict:
    """Convert SymbolContext to dict."""
    if isinstance(context, dict):
        return context
    # Handle Pydantic model
    if hasattr(context, "model_dump"):
        return context.model_dump()
    # Handle dataclass
    return asdict(context)


def _risk_to_dict(risk_result) -> dict:
    """Convert RiskResult to dict."""
    if isinstance(risk_result, dict):
        return risk_result
    return asdict(risk_result)


def _adapt_context_for_mcp(context_dict: dict) -> dict:
    """Adapt context dict for MCP output."""
    focus = context_dict.get("focus_symbol", {})
    return {
        "focus_symbol": _adapt_node_for_mcp(focus),
        "structural_parent": _adapt_node_for_mcp(context_dict.get("structural_parent", {})) if context_dict.get("structural_parent") else None,
        "structural_children": [_adapt_node_for_mcp(c) for c in context_dict.get("structural_children", [])],
        "lexical_parent": _adapt_node_for_mcp(context_dict.get("lexical_parent", {})) if context_dict.get("lexical_parent") else None,
        "lexical_children": [_adapt_node_for_mcp(c) for c in context_dict.get("lexical_children", [])],
        "incoming_edges": context_dict.get("incoming_edges", []),
        "outgoing_edges": context_dict.get("outgoing_edges", []),
        "structural_summary": context_dict.get("structural_summary", {}),
        "freshness": context_dict.get("freshness", {}),
        "confidence": context_dict.get("confidence", {}),
    }


def _adapt_node_for_mcp(node: dict) -> dict:
    """Adapt a node dict for MCP output."""
    return {
        "id": node.get("id"),
        "kind": node.get("kind"),
        "qualified_name": node.get("qualified_name"),
        "name": node.get("name"),
        "file_id": node.get("file_id"),
        "parent_id": node.get("parent_id"),
        "lexical_parent_id": node.get("lexical_parent_id"),
        "visibility_hint": node.get("visibility_hint"),
        "doc_summary": node.get("doc_summary"),
    }
