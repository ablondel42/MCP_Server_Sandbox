"""Risk target normalization and loading.

Provides functions to:
- Load and normalize symbol targets from the database
- Determine if a target is public-like
"""

import sqlite3

from repo_context.graph.risk_types import RiskTarget


def load_risk_targets(conn: sqlite3.Connection, symbol_ids: list[str]) -> list[RiskTarget]:
    """Load and normalize risk targets from symbol IDs.

    Args:
        conn: SQLite connection.
        symbol_ids: List of symbol IDs to load.

    Returns:
        List of normalized RiskTarget objects.

    Raises:
        ValueError: If any symbol ID is not found.
    """
    targets = []
    seen_ids = set()

    for symbol_id in symbol_ids:
        # Skip duplicates while preserving order
        if symbol_id in seen_ids:
            continue
        seen_ids.add(symbol_id)

        # Load symbol from database
        cursor = conn.execute(
            """
            SELECT id, repo_id, file_id, language, kind, name, qualified_name, uri,
                   parent_id, visibility_hint, doc_summary, content_hash, semantic_hash,
                   source, confidence, payload_json, scope, lexical_parent_id,
                   range_json, selection_range_json
            FROM nodes
            WHERE id = ?
            """,
            (symbol_id,),
        )
        row = cursor.fetchone()

        if row is None:
            raise ValueError(f"Symbol not found: {symbol_id}")

        # Extract file path and module path from payload_json
        import json
        payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
        file_path = payload.get("file_path", "")
        module_path = payload.get("module_path", "")

        # Create normalized target
        target = RiskTarget(
            symbol_id=row["id"],
            qualified_name=row["qualified_name"],
            kind=row["kind"],
            scope=row["scope"] or "module",
            file_id=row["file_id"],
            file_path=file_path,
            module_path=module_path,
            visibility_hint=row["visibility_hint"],
            lexical_parent_id=row["lexical_parent_id"],
        )
        targets.append(target)

    return targets


def is_public_like(target: RiskTarget) -> bool:
    """Determine if a target is public-like.

    A target is public-like if:
    - visibility_hint == "public", OR
    - name does not start with "_" (unless it's a magic method)

    Special rules:
    - Magic methods (__init__, __repr__, etc.) are public-like
    - Local scope (scope == "function") defaults to NOT public-like
      unless visibility_hint explicitly says "public"

    Args:
        target: Normalized risk target.

    Returns:
        True if target is public-like, False otherwise.
    """
    # Explicit public visibility hint
    if target.visibility_hint == "public":
        return True

    # Local scope defaults to not public
    if target.scope == "function":
        return False

    # Extract short name from qualified name
    short_name = target.qualified_name.split(".")[-1] if target.qualified_name else ""

    # Magic methods are public-like
    if short_name.startswith("__") and short_name.endswith("__"):
        return True

    # Names not starting with _ are public-like
    if not short_name.startswith("_"):
        return True

    return False
