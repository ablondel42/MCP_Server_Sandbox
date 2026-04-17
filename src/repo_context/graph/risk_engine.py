"""Risk engine main entry points.

Provides the primary API for risk analysis:
- analyze_symbol_risk: Analyze a single symbol
- analyze_target_set_risk: Analyze multiple symbols
"""

import sqlite3

from repo_context.graph.risk_types import RiskResult
from repo_context.graph.risk_targets import load_risk_targets
from repo_context.graph.risk_facts import build_risk_facts
from repo_context.graph.risk_rules import detect_risk_issues
from repo_context.graph.risk_scoring import score_risk, decide_risk


def analyze_symbol_risk(conn: sqlite3.Connection, symbol_id: str) -> RiskResult:
    """Analyze risk for a single symbol.

    Args:
        conn: SQLite connection.
        symbol_id: Symbol ID to analyze.

    Returns:
        RiskResult with analysis for the single symbol.
    """
    return analyze_target_set_risk(conn, [symbol_id])


def analyze_target_set_risk(conn: sqlite3.Connection, symbol_ids: list[str]) -> RiskResult:
    """Analyze risk for a set of symbols.

    Pipeline:
    1. Load and normalize targets
    2. Build risk facts
    3. Detect issues
    4. Compute score
    5. Determine decision
    6. Assemble result

    Args:
        conn: SQLite connection.
        symbol_ids: List of symbol IDs to analyze.

    Returns:
        RiskResult with complete analysis.
    """
    # Step 1: Load and normalize targets
    targets = load_risk_targets(conn, symbol_ids)

    # Step 2: Build facts
    facts = build_risk_facts(conn, targets)

    # Step 3: Detect issues
    issues = detect_risk_issues(facts)

    # Step 4: Compute score
    risk_score = score_risk(issues, facts)

    # Step 5: Determine decision
    decision = decide_risk(issues, facts, risk_score)

    # Step 6: Assemble result
    result = RiskResult(
        targets=targets,
        facts=facts,
        issues=issues,
        risk_score=risk_score,
        decision=decision,
    )

    return result
