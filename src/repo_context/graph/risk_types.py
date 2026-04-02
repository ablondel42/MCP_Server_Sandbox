"""Risk engine data types.

Defines the core data contracts for risk analysis:
- RiskTarget: Normalized target symbol information
- RiskFacts: Extracted risk facts
- RiskResult: Final risk assessment result
"""

from dataclasses import dataclass, field


@dataclass
class RiskTarget:
    """Normalized risk analysis target.

    Attributes:
        symbol_id: Full symbol ID (e.g., "sym:repo:test:function:my_func").
        qualified_name: Fully qualified name (e.g., "my_module.my_func").
        kind: Symbol kind (function, class, method, etc.).
        scope: Lexical scope (module, class, or function).
        file_id: File ID (e.g., "file:src/my_module.py").
        file_path: Repo-relative file path.
        module_path: Python module path (e.g., "src.my_module").
        visibility_hint: Visibility hint (public, private, etc.).
        lexical_parent_id: Parent symbol ID for nested declarations.
    """
    symbol_id: str
    qualified_name: str
    kind: str
    scope: str
    file_id: str
    file_path: str
    module_path: str
    visibility_hint: str | None = None
    lexical_parent_id: str | None = None


@dataclass
class RiskFacts:
    """Extracted risk facts for a set of targets.

    Attributes:
        target_count: Number of targets analyzed.
        symbol_ids: List of all target symbol IDs.
        symbol_kinds: Set of distinct symbol kinds.
        reference_counts: Dict mapping symbol_id to reference count.
        reference_availability: Dict mapping symbol_id to availability bool.
        referencing_file_counts: Dict mapping symbol_id to referencing file count.
        referencing_module_counts: Dict mapping symbol_id to referencing module count.
        touches_public_surface: True if any target is public-like.
        touches_local_scope_only: True if all targets are function-scoped.
        target_spans_multiple_files: True if targets span multiple files.
        target_spans_multiple_modules: True if targets span multiple modules.
        cross_file_impact: True if references cross file boundaries.
        cross_module_impact: True if references cross module boundaries.
        inheritance_involved: True if any target has inheritance.
        stale_symbols: List of stale symbol IDs.
        low_confidence_symbols: List of low-confidence symbol IDs.
        low_confidence_edges: List of low-confidence edge IDs.
        extra: Additional deterministic facts (e.g., availability metadata).
    """
    target_count: int = 0
    symbol_ids: list[str] = field(default_factory=list)
    symbol_kinds: set[str] = field(default_factory=set)
    reference_counts: dict[str, int] = field(default_factory=dict)
    reference_availability: dict[str, bool] = field(default_factory=dict)
    referencing_file_counts: dict[str, int] = field(default_factory=dict)
    referencing_module_counts: dict[str, int] = field(default_factory=dict)
    touches_public_surface: bool = False
    touches_local_scope_only: bool = False
    target_spans_multiple_files: bool = False
    target_spans_multiple_modules: bool = False
    cross_file_impact: bool = False
    cross_module_impact: bool = False
    inheritance_involved: bool = False
    stale_symbols: list[str] = field(default_factory=list)
    low_confidence_symbols: list[str] = field(default_factory=list)
    low_confidence_edges: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


@dataclass
class RiskResult:
    """Risk analysis result.

    Attributes:
        targets: List of analyzed targets.
        facts: Extracted risk facts.
        issues: List of detected issue codes.
        risk_score: Numeric risk score (0-100).
        decision: Recommended decision (safe_enough, review_required, high_risk).
    """
    targets: list[RiskTarget] = field(default_factory=list)
    facts: RiskFacts = field(default_factory=RiskFacts)
    issues: list[str] = field(default_factory=list)
    risk_score: int = 0
    decision: str = "unknown"
