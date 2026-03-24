"""Plan assessment model."""

from dataclasses import dataclass, field


@dataclass
class PlanAssessment:
    """Represents a risk assessment for a change plan."""

    plan_summary: str
    target_symbols: list[str] = field(default_factory=list)
    resolved_symbols: list[str] = field(default_factory=list)
    unresolved_targets: list[str] = field(default_factory=list)
    facts_json: str = "{}"
    issues: list[str] = field(default_factory=list)
    risk_score: int = 0
    decision: str = "unknown"
