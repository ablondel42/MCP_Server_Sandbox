"""Model tests."""

import dataclasses

import pytest

from repo_context.models import (
    Position,
    Range,
    RepoRecord,
    FileRecord,
    SymbolNode,
    Edge,
    SymbolContext,
    PlanAssessment,
    to_json,
    from_json,
)


def test_position() -> None:
    """Test Position dataclass."""
    pos = Position(line=10, character=5)
    assert pos.line == 10
    assert pos.character == 5


def test_position_is_frozen() -> None:
    """Test that Position is immutable (frozen)."""
    pos = Position(line=10, character=5)
    with pytest.raises(dataclasses.FrozenInstanceError):
        pos.line = 20  # type: ignore[misc]


def test_range() -> None:
    """Test Range dataclass."""
    start = Position(line=10, character=5)
    end = Position(line=10, character=15)
    range_obj = Range(start=start, end=end)
    assert range_obj.start.line == 10
    assert range_obj.end.character == 15


def test_range_is_frozen() -> None:
    """Test that Range is immutable (frozen)."""
    start = Position(line=10, character=5)
    end = Position(line=10, character=15)
    range_obj = Range(start=start, end=end)
    with pytest.raises(dataclasses.FrozenInstanceError):
        range_obj.start = Position(line=0, character=0)  # type: ignore[misc]


def test_repo_record() -> None:
    """Test RepoRecord dataclass."""
    repo = RepoRecord(
        id="repo:test",
        root_path="/path/to/repo",
        name="test-repo",
        default_language="python",
        created_at="2026-03-23T00:00:00Z",
    )
    assert repo.id == "repo:test"
    assert repo.last_indexed_at is None


def test_file_record() -> None:
    """Test FileRecord dataclass."""
    file_rec = FileRecord(
        id="file:app/main.py",
        repo_id="repo:test",
        file_path="app/main.py",
        uri="file:///path/to/repo/app/main.py",
        module_path="app.main",
        language="python",
        content_hash="sha256:abc123",
        size_bytes=1024,
        last_modified_at="2026-03-23T00:00:00Z",
    )
    assert file_rec.file_path == "app/main.py"
    assert file_rec.last_indexed_at is None


def test_symbol_node() -> None:
    """Test SymbolNode dataclass."""
    node = SymbolNode(
        id="sym:repo:class:app.Service",
        repo_id="repo:test",
        file_id="file:app/service.py",
        language="python",
        kind="class",
        name="Service",
        qualified_name="app.Service",
        uri="file:///path/to/repo/app/service.py",
        content_hash="sha256:abc123",
        semantic_hash="sha256:def456",
        source="python-ast",
        confidence=1.0,
        payload_json="{}",
        range_json=None,
        selection_range_json=None,
        parent_id=None,
        visibility_hint=None,
        doc_summary=None,
        last_indexed_at=None,
    )
    assert node.kind == "class"
    assert node.parent_id is None
    assert node.range_json is None


def test_edge() -> None:
    """Test Edge dataclass."""
    edge = Edge(
        id="edge:repo:contains:mod1->class1",
        repo_id="repo:test",
        kind="contains",
        from_id="sym:repo:module:app",
        to_id="sym:repo:class:app.Service",
        source="python-ast",
        confidence=1.0,
        payload_json="{}",
        evidence_file_id=None,
        evidence_uri=None,
        evidence_range_json=None,
        last_indexed_at=None,
    )
    assert edge.kind == "contains"
    assert edge.evidence_file_id is None


def test_symbol_context() -> None:
    """Test SymbolContext dataclass with proper defaults."""
    ctx = SymbolContext(focus_symbol={"id": "sym:repo:class:app.Service"})
    assert ctx.focus_symbol["id"] == "sym:repo:class:app.Service"
    assert ctx.structural_parent is None
    assert ctx.structural_children == []
    assert ctx.lexical_parent is None
    assert ctx.lexical_children == []
    assert ctx.incoming_edges == []
    assert ctx.outgoing_edges == []
    assert ctx.file_siblings == []
    assert ctx.structural_summary == {}
    assert ctx.freshness == {}
    assert ctx.confidence == {}


def test_plan_assessment() -> None:
    """Test PlanAssessment dataclass with proper defaults."""
    assessment = PlanAssessment(plan_summary="Test plan")
    assert assessment.plan_summary == "Test plan"
    assert assessment.target_symbols == []
    assert assessment.resolved_symbols == []
    assert assessment.unresolved_targets == []
    assert assessment.facts_json == "{}"
    assert assessment.issues == []
    assert assessment.risk_score == 0
    assert assessment.decision == "unknown"


def test_no_mutable_defaults() -> None:
    """Test that dataclasses do not have mutable defaults."""
    ctx1 = SymbolContext(focus_symbol={"id": "sym1"})
    ctx2 = SymbolContext(focus_symbol={"id": "sym2"})

    # Modify one instance
    ctx1.structural_children.append({"id": "child1"})

    # Other instance should not be affected
    assert ctx2.structural_children == []
    assert ctx1.structural_children == [{"id": "child1"}]

    assessment1 = PlanAssessment(plan_summary="Plan 1")
    assessment2 = PlanAssessment(plan_summary="Plan 2")

    assessment1.issues.append("issue1")
    assert assessment2.issues == []


def test_to_json_with_dict() -> None:
    """Test to_json with a dictionary."""
    data = {"key": "value", "number": 42}
    result = to_json(data)
    assert result == '{"key": "value", "number": 42}'


def test_to_json_with_dataclass() -> None:
    """Test to_json with a dataclass."""
    pos = Position(line=10, character=5)
    result = to_json(pos)
    assert result == '{"character": 5, "line": 10}'


def test_to_json_with_list() -> None:
    """Test to_json with a list."""
    data = [1, 2, 3]
    result = to_json(data)
    assert result == '[1, 2, 3]'


def test_to_json_with_nested_structure() -> None:
    """Test to_json with nested structure."""
    data = {"position": {"line": 10, "character": 5}}
    result = to_json(data)
    assert result == '{"position": {"character": 5, "line": 10}}'


def test_from_json_with_dict() -> None:
    """Test from_json with a dictionary string."""
    json_str = '{"key": "value", "number": 42}'
    result = from_json(json_str)
    assert result == {"key": "value", "number": 42}


def test_from_json_with_list() -> None:
    """Test from_json with a list string."""
    json_str = '[1, 2, 3]'
    result = from_json(json_str)
    assert result == [1, 2, 3]


def test_from_json_with_nested_structure() -> None:
    """Test from_json with nested structure string."""
    json_str = '{"position": {"line": 10, "character": 5}}'
    result = from_json(json_str)
    assert result == {"position": {"line": 10, "character": 5}}


def test_to_json_from_json_roundtrip() -> None:
    """Test that to_json and from_json are inverse operations."""
    original = {"key": "value", "nested": {"a": 1, "b": 2}}
    json_str = to_json(original)
    result = from_json(json_str)
    assert result == original


def test_to_json_sorted_keys() -> None:
    """Test that to_json produces sorted keys."""
    data = {"z": 1, "a": 2, "m": 3}
    result = to_json(data)
    assert result == '{"a": 2, "m": 3, "z": 1}'
