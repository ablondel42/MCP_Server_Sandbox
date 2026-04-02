"""Tests for the risk engine.

Tests cover:
- Target normalization
- Public-surface heuristic
- Reference fact helpers
- Inheritance risk detection
- Freshness facts
- Confidence facts
- Fact building
- Issue detection
- Scoring
- Decision logic
- End-to-end engine tests
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
    replace_file_graph,
)
from repo_context.models.repo import RepoRecord
from repo_context.models.file import FileRecord
from repo_context.graph.risk_types import RiskTarget, RiskFacts, RiskResult
from repo_context.graph.risk_targets import load_risk_targets, is_public_like
from repo_context.graph.risk_facts import (
    get_reference_count,
    get_reference_availability,
    build_risk_facts,
)
from repo_context.graph.risk_rules import (
    detect_risk_issues,
    ISSUE_STALE_CONTEXT,
    ISSUE_LOW_CONFIDENCE_MATCH,
    ISSUE_HIGH_REFERENCE_COUNT,
    ISSUE_CROSS_FILE_IMPACT,
    ISSUE_CROSS_MODULE_IMPACT,
    ISSUE_PUBLIC_SURFACE_CHANGE,
    ISSUE_INHERITANCE_RISK,
    ISSUE_MULTI_FILE_CHANGE,
    ISSUE_MULTI_MODULE_CHANGE,
    ISSUE_REFERENCE_DATA_UNAVAILABLE,
)
from repo_context.graph.risk_scoring import (
    score_risk,
    decide_risk,
    DECISION_SAFE_ENOUGH,
    DECISION_REVIEW_REQUIRED,
    DECISION_HIGH_RISK,
)
from repo_context.graph.risk_engine import analyze_symbol_risk, analyze_target_set_risk


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
    """Create a minimal test graph with symbols and references."""
    import datetime
    
    # Create repo
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    repo = RepoRecord(id=repo_id, root_path="/test", name="test", default_language="python", created_at=now)
    upsert_repo(conn, repo)

    # Create files
    now = "2024-01-01T00:00:00Z"
    file1 = FileRecord(
        id="file:src/module1.py",
        repo_id=repo_id,
        file_path="src/module1.py",
        uri="file:///test/src/module1.py",
        module_path="src.module1",
        language="python",
        content_hash="sha256:abc123",
        size_bytes=1000,
        last_modified_at=now,
    )
    file2 = FileRecord(
        id="file:src/module2.py",
        repo_id=repo_id,
        file_path="src/module2.py",
        uri="file:///test/src/module2.py",
        module_path="src.module2",
        language="python",
        content_hash="sha256:def456",
        size_bytes=1000,
        last_modified_at=now,
    )
    upsert_files(conn, [file1, file2])

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
            "last_indexed_at": "2024-01-01T00:00:00Z",
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
            "last_indexed_at": "2024-01-01T00:00:00Z",
        },
        {
            "id": "sym:repo:test:function:src.module2.func2",
            "repo_id": repo_id,
            "file_id": file2.id,
            "language": "python",
            "kind": "function",
            "name": "func2",
            "qualified_name": "src.module2.func2",
            "uri": "file:///test/src/module2.py",
            "range_json": json.dumps({"start": {"line": 0, "character": 0}, "end": {"line": 10, "character": 0}}),
            "selection_range_json": json.dumps({"start": {"line": 0, "character": 4}, "end": {"line": 0, "character": 9}}),
            "parent_id": "sym:repo:test:module:src.module2",
            "visibility_hint": "public",
            "doc_summary": "Test function",
            "content_hash": "sha256:def",
            "semantic_hash": "sha256:def",
            "source": "python-ast",
            "confidence": 1.0,
            "payload_json": json.dumps({"file_path": "src/module2.py", "module_path": "src.module2"}),
            "scope": "module",
            "lexical_parent_id": None,
            "last_indexed_at": "2024-01-01T00:00:00Z",
        },
        {
            "id": "sym:repo:test:module:src.module2",
            "repo_id": repo_id,
            "file_id": file2.id,
            "language": "python",
            "kind": "module",
            "name": "module2",
            "qualified_name": "src.module2",
            "uri": "file:///test/src/module2.py",
            "range_json": json.dumps({"start": {"line": 0, "character": 0}, "end": {"line": 100, "character": 0}}),
            "selection_range_json": json.dumps({"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}}),
            "parent_id": None,
            "visibility_hint": "public",
            "doc_summary": None,
            "content_hash": "sha256:def456",
            "semantic_hash": "sha256:def456",
            "source": "python-ast",
            "confidence": 1.0,
            "payload_json": json.dumps({"file_path": "src/module2.py", "module_path": "src.module2"}),
            "scope": "module",
            "lexical_parent_id": None,
            "last_indexed_at": "2024-01-01T00:00:00Z",
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

    # Create a reference edge from func2 to func1
    conn.execute(
        """
        INSERT INTO edges (
            id, repo_id, kind, from_id, to_id, source, confidence,
            evidence_file_id, evidence_uri, evidence_range_json, payload_json, last_indexed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "edge:repo:test:references:sym:repo:test:function:src.module2.func2->sym:repo:test:function:src.module1.func1:5:10",
            repo_id,
            "references",
            "sym:repo:test:function:src.module2.func2",
            "sym:repo:test:function:src.module1.func1",
            "lsp",
            0.9,
            file2.id,
            file2.uri,
            json.dumps({"start": {"line": 5, "character": 10}, "end": {"line": 5, "character": 15}}),
            json.dumps({"mapping_mode": "exact_symbol"}),
            "2024-01-01T00:00:00Z",
        ),
    )

    # Create reference_refresh record
    conn.execute(
        """
        INSERT INTO reference_refresh (target_symbol_id, available, last_refreshed_at)
        VALUES (?, ?, ?)
        """,
        ("sym:repo:test:function:src.module1.func1", 1, "2024-01-01T00:00:00Z"),
    )

    conn.commit()


# ==================== Target Normalization Tests ====================

def test_load_risk_targets_single_symbol(initialized_conn):
    """Test loading a single risk target."""
    conn, _ = initialized_conn
    _create_test_graph(conn)

    targets = load_risk_targets(conn, ["sym:repo:test:function:src.module1.func1"])

    assert len(targets) == 1
    target = targets[0]
    assert target.symbol_id == "sym:repo:test:function:src.module1.func1"
    assert target.qualified_name == "src.module1.func1"
    assert target.kind == "function"
    assert target.scope == "module"
    assert target.visibility_hint == "public"


def test_load_risk_targets_multiple_symbols(initialized_conn):
    """Test loading multiple risk targets."""
    conn, _ = initialized_conn
    _create_test_graph(conn)

    targets = load_risk_targets(conn, [
        "sym:repo:test:function:src.module1.func1",
        "sym:repo:test:function:src.module2.func2",
    ])

    assert len(targets) == 2


def test_load_risk_targets_deduplicates(initialized_conn):
    """Test that duplicate symbol IDs are removed."""
    conn, _ = initialized_conn
    _create_test_graph(conn)

    targets = load_risk_targets(conn, [
        "sym:repo:test:function:src.module1.func1",
        "sym:repo:test:function:src.module1.func1",
    ])

    assert len(targets) == 1


def test_load_risk_targets_raises_on_not_found(initialized_conn):
    """Test that loading non-existent symbol raises ValueError."""
    conn, _ = initialized_conn

    with pytest.raises(ValueError, match="Symbol not found"):
        load_risk_targets(conn, ["sym:repo:test:function:nonexistent"])


# ==================== Public Surface Heuristic Tests ====================

def test_is_public_like_explicit_public():
    """Test that explicit public visibility is public-like."""
    target = RiskTarget(
        symbol_id="sym:test",
        qualified_name="test.func",
        kind="function",
        scope="module",
        file_id="file:test.py",
        file_path="test.py",
        module_path="test",
        visibility_hint="public",
    )
    assert is_public_like(target) is True


def test_is_public_like_no_underscore():
    """Test that names without underscore are public-like."""
    target = RiskTarget(
        symbol_id="sym:test",
        qualified_name="test.myfunc",
        kind="function",
        scope="module",
        file_id="file:test.py",
        file_path="test.py",
        module_path="test",
        visibility_hint=None,
    )
    assert is_public_like(target) is True


def test_is_public_like_private_name():
    """Test that names with underscore are not public-like."""
    target = RiskTarget(
        symbol_id="sym:test",
        qualified_name="test._private",
        kind="function",
        scope="module",
        file_id="file:test.py",
        file_path="test.py",
        module_path="test",
        visibility_hint=None,
    )
    assert is_public_like(target) is False


def test_is_public_like_magic_method():
    """Test that magic methods are public-like."""
    target = RiskTarget(
        symbol_id="sym:test",
        qualified_name="test.Class.__init__",
        kind="method",
        scope="class",
        file_id="file:test.py",
        file_path="test.py",
        module_path="test",
        visibility_hint=None,
    )
    assert is_public_like(target) is True


def test_is_public_like_local_scope_defaults_private():
    """Test that local scope defaults to not public-like."""
    target = RiskTarget(
        symbol_id="sym:test",
        qualified_name="test.outer.inner_func",
        kind="local_function",
        scope="function",
        file_id="file:test.py",
        file_path="test.py",
        module_path="test",
        visibility_hint=None,
    )
    assert is_public_like(target) is False


# ==================== Issue Detection Tests ====================

def test_detect_issues_empty_facts():
    """Test issue detection with empty facts."""
    facts = RiskFacts()
    issues = detect_risk_issues(facts)
    assert issues == []


def test_detect_issues_stale_context():
    """Test stale_context issue detection."""
    facts = RiskFacts(stale_symbols=["sym:stale"])
    issues = detect_risk_issues(facts)
    assert ISSUE_STALE_CONTEXT in issues


def test_detect_issues_low_confidence_match():
    """Test low_confidence_match issue detection."""
    facts = RiskFacts(low_confidence_symbols=["sym:low"])
    issues = detect_risk_issues(facts)
    assert ISSUE_LOW_CONFIDENCE_MATCH in issues


def test_detect_issues_public_surface_change():
    """Test public_surface_change issue detection."""
    facts = RiskFacts(touches_public_surface=True)
    issues = detect_risk_issues(facts)
    assert ISSUE_PUBLIC_SURFACE_CHANGE in issues


def test_detect_issues_cross_file_impact():
    """Test cross_file_impact issue detection."""
    facts = RiskFacts(cross_file_impact=True)
    issues = detect_risk_issues(facts)
    assert ISSUE_CROSS_FILE_IMPACT in issues


def test_detect_issues_inheritance_risk():
    """Test inheritance_risk issue detection."""
    facts = RiskFacts(inheritance_involved=True)
    issues = detect_risk_issues(facts)
    assert ISSUE_INHERITANCE_RISK in issues


def test_detect_issues_reference_data_unavailable():
    """Test reference_data_unavailable issue detection."""
    facts = RiskFacts(
        reference_availability={"sym:1": False, "sym:2": True}
    )
    issues = detect_risk_issues(facts)
    assert ISSUE_REFERENCE_DATA_UNAVAILABLE in issues


# ==================== Scoring Tests ====================

def test_score_risk_empty_issues():
    """Test scoring with no issues."""
    facts = RiskFacts()
    score = score_risk([], facts)
    assert score == 0


def test_score_risk_single_issue():
    """Test scoring with single issue."""
    facts = RiskFacts()
    score = score_risk([ISSUE_STALE_CONTEXT], facts)
    assert score == 20


def test_score_risk_multiple_issues():
    """Test scoring with multiple issues."""
    facts = RiskFacts()
    issues = [ISSUE_STALE_CONTEXT, ISSUE_PUBLIC_SURFACE_CHANGE]
    score = score_risk(issues, facts)
    assert score == 35  # 20 + 15


def test_score_risk_clamped_to_100():
    """Test that score is clamped to 100."""
    facts = RiskFacts()
    issues = [
        ISSUE_STALE_CONTEXT,  # 20
        ISSUE_LOW_CONFIDENCE_MATCH,  # 20
        ISSUE_HIGH_REFERENCE_COUNT,  # 20
        ISSUE_CROSS_MODULE_IMPACT,  # 15
        ISSUE_PUBLIC_SURFACE_CHANGE,  # 15
        ISSUE_MULTI_MODULE_CHANGE,  # 15
    ]
    score = score_risk(issues, facts)
    assert score == 100  # Would be 105, clamped to 100


def test_score_risk_local_scope_mitigation():
    """Test local scope mitigation."""
    facts = RiskFacts(
        touches_local_scope_only=True,
        touches_public_surface=False,
    )
    issues = [ISSUE_STALE_CONTEXT]  # 20
    score = score_risk(issues, facts)
    assert score == 10  # 20 - 10 mitigation


# ==================== Decision Tests ====================

def test_decide_risk_safe_enough():
    """Test safe_enough decision for low scores."""
    facts = RiskFacts()
    decision = decide_risk([], facts, 15)
    assert decision == DECISION_SAFE_ENOUGH


def test_decide_risk_review_required():
    """Test review_required decision for medium scores."""
    facts = RiskFacts()
    decision = decide_risk([], facts, 50)
    assert decision == DECISION_REVIEW_REQUIRED


def test_decide_risk_high_risk():
    """Test high_risk decision for high scores."""
    facts = RiskFacts()
    decision = decide_risk([], facts, 80)
    assert decision == DECISION_HIGH_RISK


def test_decide_risk_stale_context_override():
    """Test that stale_context forces at least review_required."""
    facts = RiskFacts()
    issues = [ISSUE_STALE_CONTEXT]
    decision = decide_risk(issues, facts, 10)  # Score would be safe_enough
    assert decision == DECISION_REVIEW_REQUIRED


# ==================== End-to-End Engine Tests ====================

def test_analyze_symbol_risk_end_to_end(initialized_conn):
    """Test end-to-end symbol risk analysis."""
    conn, _ = initialized_conn
    _create_test_graph(conn)

    result = analyze_symbol_risk(conn, "sym:repo:test:function:src.module1.func1")

    assert result.risk_score >= 0
    assert result.risk_score <= 100
    assert result.decision in (DECISION_SAFE_ENOUGH, DECISION_REVIEW_REQUIRED, DECISION_HIGH_RISK)
    assert len(result.targets) == 1
    assert result.targets[0].symbol_id == "sym:repo:test:function:src.module1.func1"


def test_analyze_target_set_risk_end_to_end(initialized_conn):
    """Test end-to-end target set risk analysis."""
    conn, _ = initialized_conn
    _create_test_graph(conn)

    result = analyze_target_set_risk(conn, [
        "sym:repo:test:function:src.module1.func1",
        "sym:repo:test:function:src.module2.func2",
    ])

    assert result.facts.target_count == 2
    assert len(result.targets) == 2
