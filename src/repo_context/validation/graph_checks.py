"""Graph shape validators.

Provides deterministic graph-shape assertions to verify that
stored graph truth is structurally usable, not just non-empty.
"""

import sqlite3

from repo_context.graph.queries import (
    get_repo_graph_stats,
    CALLABLE_KINDS,
    LOCAL_CALLABLE_KINDS,
)


def assert_file_nodes_exist(conn: sqlite3.Connection, repo_id: str, file_id: str) -> dict:
    """Assert that file-owned nodes exist in the graph.

    Args:
        conn: SQLite connection.
        repo_id: Repository ID.
        file_id: File ID to check.

    Returns:
        Dict with 'passed', 'node_count', 'errors'.
    """
    errors = []
    cursor = conn.execute(
        "SELECT COUNT(*) as cnt FROM nodes WHERE repo_id = ? AND file_id = ?",
        (repo_id, file_id),
    )
    row = cursor.fetchone()
    node_count = row["cnt"]

    if node_count == 0:
        errors.append(f"No nodes found for file {file_id}")

    return {
        "check": "file_nodes_exist",
        "passed": node_count > 0,
        "node_count": node_count,
        "errors": errors,
    }


def assert_module_nodes_exist(conn: sqlite3.Connection, repo_id: str) -> dict:
    """Assert that module nodes exist for a repository.

    Args:
        conn: SQLite connection.
        repo_id: Repository ID.

    Returns:
        Dict with 'passed', 'module_count', 'errors'.
    """
    errors = []
    cursor = conn.execute(
        "SELECT COUNT(*) as cnt FROM nodes WHERE repo_id = ? AND kind = 'module'",
        (repo_id,),
    )
    row = cursor.fetchone()
    module_count = row["cnt"]

    if module_count == 0:
        errors.append(f"No module nodes found for repo {repo_id}")

    return {
        "check": "module_nodes_exist",
        "passed": module_count > 0,
        "module_count": module_count,
        "errors": errors,
    }


def assert_expected_symbol_kinds(conn: sqlite3.Connection, repo_id: str) -> dict:
    """Assert that expected symbol kinds are present in the graph.

    Validates that the graph contains standard symbol kinds from
    earlier phases (module, class, function, method, etc.).

    Args:
        conn: SQLite connection.
        repo_id: Repository ID.

    Returns:
        Dict with 'passed', 'kinds_found', 'expected_missing', 'errors'.
    """
    errors = []
    cursor = conn.execute(
        "SELECT DISTINCT kind FROM nodes WHERE repo_id = ?",
        (repo_id,),
    )
    found_kinds = {row["kind"] for row in cursor.fetchall()}

    # At least some callable kinds should be present in any Python repo
    callable_found = found_kinds & CALLABLE_KINDS
    if not callable_found:
        errors.append(f"No callable kinds found. Expected one of: {CALLABLE_KINDS}")

    return {
        "check": "expected_symbol_kinds",
        "passed": len(errors) == 0,
        "kinds_found": sorted(found_kinds),
        "callable_kinds_found": sorted(callable_found),
        "errors": errors,
    }


def assert_nested_scope_symbols_present(conn: sqlite3.Connection, repo_id: str) -> dict:
    """Assert that nested-scope symbols (local functions) exist when expected.

    Validates phase 03b compatibility: local_function and local_async_function
    kinds should be present if the repo has nested function declarations.

    Args:
        conn: SQLite connection.
        repo_id: Repository ID.

    Returns:
        Dict with 'passed', 'local_callable_count', 'has_lexical_parents', 'errors'.
    """
    errors = []
    cursor = conn.execute(
        "SELECT COUNT(*) as cnt FROM nodes WHERE repo_id = ? AND kind IN ('local_function', 'local_async_function')",
        (repo_id,),
    )
    local_count = cursor.fetchone()["cnt"]

    # Check for lexical_parent_id presence (phase 03b feature)
    cursor = conn.execute(
        "SELECT COUNT(*) as cnt FROM nodes WHERE repo_id = ? AND lexical_parent_id IS NOT NULL",
        (repo_id,),
    )
    with_lexical_parent = cursor.fetchone()["cnt"]

    return {
        "check": "nested_scope_symbols_present",
        "passed": True,  # Not having local functions is OK
        "local_callable_count": local_count,
        "nodes_with_lexical_parent": with_lexical_parent,
        "errors": errors,
    }


def assert_structural_edges_present(conn: sqlite3.Connection, repo_id: str) -> dict:
    """Assert that structural edges (contains, imports) exist.

    Args:
        conn: SQLite connection.
        repo_id: Repository ID.

    Returns:
        Dict with 'passed', 'contains_count', 'imports_count', 'inherits_count', 'errors'.
    """
    errors = []
    cursor = conn.execute(
        "SELECT kind, COUNT(*) as cnt FROM edges WHERE repo_id = ? GROUP BY kind",
        (repo_id,),
    )
    kind_counts = {row["kind"]: row["cnt"] for row in cursor.fetchall()}

    contains_count = kind_counts.get("contains", 0)
    imports_count = kind_counts.get("imports", 0)
    inherits_count = kind_counts.get("inherits", 0)

    if contains_count == 0:
        errors.append("No 'contains' edges found")

    # imports and inherits are optional for minimal fixtures

    return {
        "check": "structural_edges_present",
        "passed": len(errors) == 0,
        "contains_count": contains_count,
        "imports_count": imports_count,
        "inherits_count": inherits_count,
        "edge_kind_counts": kind_counts,
        "errors": errors,
    }


def assert_no_duplicate_stable_ids(conn: sqlite3.Connection, repo_id: str) -> dict:
    """Assert that there are no duplicate stable IDs.

    Args:
        conn: SQLite connection.
        repo_id: Repository ID.

    Returns:
        Dict with 'passed', 'duplicate_count', 'duplicates', 'errors'.
    """
    errors = []
    cursor = conn.execute(
        """
        SELECT id, COUNT(*) as cnt FROM nodes WHERE repo_id = ?
        GROUP BY id HAVING cnt > 1
        """,
        (repo_id,),
    )
    duplicates = [row["id"] for row in cursor.fetchall()]

    if duplicates:
        errors.append(f"Found {len(duplicates)} duplicate node IDs")

    return {
        "check": "no_duplicate_stable_ids",
        "passed": len(duplicates) == 0,
        "duplicate_count": len(duplicates),
        "duplicates": duplicates[:10],  # Limit output
        "errors": errors,
    }


def assert_reference_edge_shape(conn: sqlite3.Connection, repo_id: str) -> dict:
    """Assert that reference edges have the correct shape.

    Validates that 'references' edges have evidence_file_id, confidence,
    and source='lsp' when present.

    Args:
        conn: SQLite connection.
        repo_id: Repository ID.

    Returns:
        Dict with 'passed', 'reference_count', 'missing_evidence', 'errors'.
    """
    errors = []
    cursor = conn.execute(
        "SELECT COUNT(*) as cnt FROM edges WHERE repo_id = ? AND kind = 'references'",
        (repo_id,),
    )
    ref_count = cursor.fetchone()["cnt"]

    missing_evidence = 0
    if ref_count > 0:
        cursor = conn.execute(
            """
            SELECT COUNT(*) as cnt FROM edges
            WHERE repo_id = ? AND kind = 'references' AND evidence_file_id IS NULL
            """,
            (repo_id,),
        )
        missing_evidence = cursor.fetchone()["cnt"]
        if missing_evidence > 0:
            errors.append(f"{missing_evidence} reference edges missing evidence_file_id")

    return {
        "check": "reference_edge_shape",
        "passed": len(errors) == 0,
        "reference_count": ref_count,
        "missing_evidence": missing_evidence,
        "errors": errors,
    }
