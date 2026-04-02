"""Risk fact extraction.

Provides functions to extract deterministic facts from stored graph data:
- Reference counts and availability
- Inheritance involvement
- Freshness (stale symbols)
- Confidence issues
"""

import sqlite3
import json

from repo_context.graph.risk_types import RiskTarget, RiskFacts
from repo_context.graph.risk_targets import is_public_like


def get_reference_count(conn: sqlite3.Connection, target_id: str) -> int:
    """Get the number of references to a target symbol.

    Args:
        conn: SQLite connection.
        target_id: Target symbol ID.

    Returns:
        Number of stored 'references' edges where to_id = target_id.
    """
    cursor = conn.execute(
        "SELECT COUNT(*) FROM edges WHERE kind = 'references' AND to_id = ?",
        (target_id,),
    )
    return cursor.fetchone()[0]


def get_reference_availability(conn: sqlite3.Connection, target_id: str) -> bool:
    """Get reference enrichment availability for a target.

    Args:
        conn: SQLite connection.
        target_id: Target symbol ID.

    Returns:
        True if references were successfully refreshed, False if never refreshed.
    """
    cursor = conn.execute(
        "SELECT available FROM reference_refresh WHERE target_symbol_id = ?",
        (target_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return False
    return bool(row["available"])


def get_referencing_file_count(conn: sqlite3.Connection, target_id: str) -> int:
    """Get the number of unique files referencing a target.

    Args:
        conn: SQLite connection.
        target_id: Target symbol ID.

    Returns:
        Count of distinct evidence_file_id values for references to target.
    """
    cursor = conn.execute(
        """
        SELECT COUNT(DISTINCT evidence_file_id)
        FROM edges
        WHERE kind = 'references' AND to_id = ?
        """,
        (target_id,),
    )
    return cursor.fetchone()[0]


def get_referencing_module_count(conn: sqlite3.Connection, target_id: str) -> int:
    """Get the number of unique modules referencing a target.

    Args:
        conn: SQLite connection.
        target_id: Target symbol ID.

    Returns:
        Count of distinct source modules for references to target.
    """
    cursor = conn.execute(
        """
        SELECT COUNT(DISTINCT n.file_id)
        FROM edges e
        JOIN nodes n ON e.from_id = n.id
        WHERE e.kind = 'references' AND e.to_id = ?
        """,
        (target_id,),
    )
    return cursor.fetchone()[0]


def target_has_inheritance_risk(conn: sqlite3.Connection, target: RiskTarget) -> bool:
    """Check if a target has inheritance involvement.

    For classes: checks if class has outgoing 'inherits' edges.
    For methods: checks if parent class has outgoing 'inherits' edges.
    For local functions/classes: returns False (not tracked in v1).

    Args:
        conn: SQLite connection.
        target: Normalized risk target.

    Returns:
        True if inheritance is involved, False otherwise.
    """
    # Local functions/classes don't have inheritance in v1
    if target.scope == "function":
        return False

    # For classes, check direct inheritance edges
    if target.kind == "class":
        cursor = conn.execute(
            "SELECT COUNT(*) FROM edges WHERE kind = 'inherits' AND from_id = ?",
            (target.symbol_id,),
        )
        return cursor.fetchone()[0] > 0

    # For methods, check if parent class has inheritance
    if target.kind in ("method", "async_method"):
        # Get the parent class
        cursor = conn.execute(
            "SELECT parent_id FROM nodes WHERE id = ?",
            (target.symbol_id,),
        )
        row = cursor.fetchone()
        if row and row["parent_id"]:
            parent_id = row["parent_id"]
            cursor = conn.execute(
                "SELECT COUNT(*) FROM edges WHERE kind = 'inherits' AND from_id = ?",
                (parent_id,),
            )
            return cursor.fetchone()[0] > 0

    return False


def collect_stale_symbols(conn: sqlite3.Connection, targets: list[RiskTarget]) -> list[str]:
    """Collect symbol IDs that are stale (missing last_indexed_at).

    Args:
        conn: SQLite connection.
        targets: List of risk targets.

    Returns:
        List of stale symbol IDs in deterministic order.
    """
    stale = []
    for target in targets:
        cursor = conn.execute(
            "SELECT last_indexed_at FROM nodes WHERE id = ?",
            (target.symbol_id,),
        )
        row = cursor.fetchone()
        if row is None or row["last_indexed_at"] is None:
            stale.append(target.symbol_id)
    return stale


def collect_low_confidence_symbols(
    conn: sqlite3.Connection,
    targets: list[RiskTarget],
    threshold: float = 0.8,
) -> list[str]:
    """Collect symbol IDs with low confidence.

    Args:
        conn: SQLite connection.
        targets: List of risk targets.
        threshold: Confidence threshold (symbols below this are flagged).

    Returns:
        List of low-confidence symbol IDs in deterministic order.
    """
    low_conf = []
    for target in targets:
        cursor = conn.execute(
            "SELECT confidence FROM nodes WHERE id = ?",
            (target.symbol_id,),
        )
        row = cursor.fetchone()
        if row and row["confidence"] is not None and row["confidence"] < threshold:
            low_conf.append(target.symbol_id)
    return low_conf


def collect_low_confidence_edges(
    conn: sqlite3.Connection,
    targets: list[RiskTarget],
    threshold: float = 0.8,
) -> list[str]:
    """Collect edge IDs with low confidence.

    Checks 'references' edges where to_id is in the target set.

    Args:
        conn: SQLite connection.
        targets: List of risk targets.
        threshold: Confidence threshold (edges below this are flagged).

    Returns:
        List of low-confidence edge IDs in deterministic order.
    """
    if not targets:
        return []

    target_ids = [t.symbol_id for t in targets]
    placeholders = ",".join("?" * len(target_ids))

    cursor = conn.execute(
        f"""
        SELECT id, confidence FROM edges
        WHERE kind = 'references' AND to_id IN ({placeholders})
        ORDER BY id
        """,
        target_ids,
    )

    low_conf = []
    for row in cursor.fetchall():
        if row["confidence"] is not None and row["confidence"] < threshold:
            low_conf.append(row["id"])

    return low_conf


def build_risk_facts(conn: sqlite3.Connection, targets: list[RiskTarget]) -> RiskFacts:
    """Build comprehensive risk facts for a set of targets.

    Args:
        conn: SQLite connection.
        targets: List of normalized risk targets.

    Returns:
        Populated RiskFacts object.
    """
    if not targets:
        return RiskFacts()

    facts = RiskFacts(
        target_count=len(targets),
        symbol_ids=[t.symbol_id for t in targets],
        symbol_kinds={t.kind for t in targets},
    )

    # Collect per-target reference facts
    all_file_ids = set()
    all_module_paths = set()
    any_public = False
    all_function_scope = True
    any_inheritance = False

    for target in targets:
        # Reference counts and availability
        facts.reference_counts[target.symbol_id] = get_reference_count(conn, target.symbol_id)
        facts.reference_availability[target.symbol_id] = get_reference_availability(conn, target.symbol_id)
        facts.referencing_file_counts[target.symbol_id] = get_referencing_file_count(conn, target.symbol_id)
        facts.referencing_module_counts[target.symbol_id] = get_referencing_module_count(conn, target.symbol_id)

        # Track file and module spread
        all_file_ids.add(target.file_id)
        all_module_paths.add(target.module_path)

        # Public surface check
        if is_public_like(target):
            any_public = True

        # Local scope check
        if target.scope != "function":
            all_function_scope = False

        # Inheritance check
        if target_has_inheritance_risk(conn, target):
            any_inheritance = True

    # Set aggregate facts
    facts.touches_public_surface = any_public
    facts.touches_local_scope_only = all_function_scope and len(targets) > 0
    facts.target_spans_multiple_files = len(all_file_ids) > 1
    facts.target_spans_multiple_modules = len(all_module_paths) > 1
    facts.inheritance_involved = any_inheritance

    # Cross-file/module impact (only if references are available)
    any_refs_available = any(facts.reference_availability.values())
    if any_refs_available:
        # Cross-file: references from files other than target's own file
        for target in targets:
            target_file = target.file_id
            ref_file_count = facts.referencing_file_counts.get(target.symbol_id, 0)
            if ref_file_count > 1:
                facts.cross_file_impact = True
                break
            # Also check if referenced from a different file
            if ref_file_count == 1:
                cursor = conn.execute(
                    """
                    SELECT DISTINCT evidence_file_id FROM edges
                    WHERE kind = 'references' AND to_id = ?
                    """,
                    (target.symbol_id,),
                )
                for row in cursor.fetchall():
                    if row["evidence_file_id"] != target_file:
                        facts.cross_file_impact = True
                        break
                if facts.cross_file_impact:
                    break

        # Cross-module: similar logic for modules
        for target in targets:
            ref_module_count = facts.referencing_module_counts.get(target.symbol_id, 0)
            if ref_module_count > 1:
                facts.cross_module_impact = True
                break

    # Collect stale and low-confidence symbols/edges
    facts.stale_symbols = collect_stale_symbols(conn, targets)
    facts.low_confidence_symbols = collect_low_confidence_symbols(conn, targets)
    facts.low_confidence_edges = collect_low_confidence_edges(conn, targets)

    # Extra metadata
    facts.extra["all_references_available"] = all(facts.reference_availability.values())
    facts.extra["any_references_unavailable"] = not all(facts.reference_availability.get(tid, False) for tid in facts.symbol_ids)

    return facts
