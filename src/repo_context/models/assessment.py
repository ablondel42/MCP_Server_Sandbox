"""Plan assessment model."""

from dataclasses import dataclass, field


@dataclass
class PlanAssessment:
    """Represents a risk assessment for a change plan.
    
    Attributes:
        plan_summary: Human-readable description of the proposed change.
        target_symbols: List of symbol IDs that the plan intends to modify.
        resolved_symbols: List of symbol IDs successfully resolved in the graph.
        unresolved_targets: List of symbol IDs that could not be resolved.
        facts_json: JSON string with discovered facts about the plan.
        issues: List of potential problems or concerns identified.
        risk_score: Numeric risk score (higher = more risky).
        decision: Recommended decision ("proceed", "review", "block", "unknown").
    """

    plan_summary: str
    target_symbols: list[str] = field(default_factory=list)
    resolved_symbols: list[str] = field(default_factory=list)
    unresolved_targets: list[str] = field(default_factory=list)
    facts_json: str = "{}"
    issues: list[str] = field(default_factory=list)
    risk_score: int = 0
    decision: str = "unknown"
