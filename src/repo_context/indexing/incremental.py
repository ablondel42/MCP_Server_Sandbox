"""Incremental reindexing for changed files.

Handles file create/modify/delete events by reindexing or cleaning up
graph state for the affected files.
"""

import sqlite3
from pathlib import Path

from repo_context.config import AppConfig
from repo_context.parsing.pipeline import extract_file_graph
from repo_context.parsing.scanner import build_file_record
from repo_context.storage import (
    upsert_files,
    replace_file_graph,
)
from repo_context.indexing.invalidation import (
    mark_symbols_in_file_stale,
    invalidate_reference_summaries_for_file,
    collect_impacted_symbol_ids,
)


def reindex_changed_file(
    conn: sqlite3.Connection,
    repo_root: Path,
    absolute_path: str,
    config: AppConfig,
) -> dict:
    """Reindex a created or modified file.

    Args:
        conn: SQLite connection.
        repo_root: Absolute path to repository root.
        absolute_path: Absolute path to the changed file.
        config: Application configuration.

    Returns:
        Structured summary with file_path, status, node_count, edge_count.
    """
    abs_path = Path(absolute_path)
    repo_relative = str(abs_path.relative_to(repo_root)).replace("\\", "/")

    # Check file exists
    if not abs_path.exists():
        return {
            "file_path": repo_relative,
            "status": "skipped",
            "node_count": 0,
            "edge_count": 0,
        }

    # Check file is supported
    is_supported = any(repo_relative.endswith(ext) for ext in config.supported_extensions)
    if not is_supported:
        return {
            "file_path": repo_relative,
            "status": "skipped",
            "node_count": 0,
            "edge_count": 0,
        }

    try:
        # Build file record
        repo_id = f"repo:{repo_root.name}"
        file_record = build_file_record(repo_id, repo_root, abs_path)

        # Upsert file record
        upsert_files(conn, [file_record])

        # Run AST extraction pipeline
        nodes, edges, _summary = extract_file_graph(file_record.repo_id, file_record, repo_root)

        # Replace file graph
        replace_file_graph(conn, file_record.id, nodes, edges)

        # Invalidate references for this file
        invalidated_count = invalidate_reference_summaries_for_file(conn, file_record.id)
        mark_symbols_in_file_stale(conn, file_record.id)
        conn.commit()

        return {
            "file_path": repo_relative,
            "status": "reindexed",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "invalidated_reference_edge_count": invalidated_count,
        }

    except SyntaxError:
        # Parse failure: keep previous graph state
        return {
            "file_path": repo_relative,
            "status": "parse_failed",
            "node_count": 0,
            "edge_count": 0,
        }

    except Exception:
        # Other error: don't destroy previous state
        return {
            "file_path": repo_relative,
            "status": "error",
            "node_count": 0,
            "edge_count": 0,
        }


def handle_deleted_file(
    conn: sqlite3.Connection,
    repo_id: str,
    repo_relative_path: str,
) -> dict:
    """Handle deletion of a tracked file.

    Args:
        conn: SQLite connection.
        repo_id: Repository ID.
        repo_relative_path: Repository-relative path of deleted file.

    Returns:
        Structured summary with file_path, status, deleted counts.
    """
    # Find file record
    cursor = conn.execute(
        "SELECT id FROM files WHERE repo_id = ? AND file_path = ?",
        (repo_id, repo_relative_path),
    )
    row = cursor.fetchone()

    if row is None:
        return {
            "file_path": repo_relative_path,
            "status": "not_tracked",
            "deleted_node_count": 0,
            "deleted_edge_count": 0,
            "invalidated_target_symbol_count": 0,
        }

    file_id = row["id"]

    try:
        # Get impacted symbols before deletion
        impacted_symbols = collect_impacted_symbol_ids(conn, file_id)

        # Remove reference edges where this file is evidence
        cursor = conn.execute(
            "DELETE FROM edges WHERE kind = 'references' AND evidence_file_id = ?",
            (file_id,),
        )
        deleted_ref_edges = cursor.rowcount

        # Count nodes to be deleted
        cursor = conn.execute(
            "SELECT COUNT(*) FROM nodes WHERE file_id = ?",
            (file_id,),
        )
        node_count = cursor.fetchone()[0]

        # Delete file-owned nodes
        conn.execute(
            "DELETE FROM nodes WHERE file_id = ?",
            (file_id,),
        )

        # Delete file-owned edges
        conn.execute(
            "DELETE FROM edges WHERE from_id IN (SELECT id FROM nodes WHERE file_id = ?) OR to_id IN (SELECT id FROM nodes WHERE file_id = ?)",
            (file_id, file_id),
        )

        # Delete file record
        conn.execute(
            "DELETE FROM files WHERE id = ?",
            (file_id,),
        )

        # Mark impacted symbols as stale
        mark_symbols_in_file_stale(conn, file_id)
        conn.commit()

        return {
            "file_path": repo_relative_path,
            "status": "deleted",
            "deleted_node_count": node_count,
            "deleted_edge_count": deleted_ref_edges,
            "invalidated_target_symbol_count": len(impacted_symbols),
        }

    except Exception:
        conn.rollback()
        return {
            "file_path": repo_relative_path,
            "status": "error",
            "deleted_node_count": 0,
            "deleted_edge_count": 0,
            "invalidated_target_symbol_count": 0,
        }


def process_event_batch(
    conn: sqlite3.Connection,
    repo_root: Path,
    events: list,
    config: AppConfig,
) -> list[dict]:
    """Process a batch of collapsed file change events.

    Processes one file at a time. Each file update is isolated in its own
    transaction scope (handled by underlying helpers).

    Args:
        conn: SQLite connection.
        repo_root: Absolute path to repository root.
        events: List of collapsed FileChangeEvent objects.
        config: Application configuration.

    Returns:
        List of per-file structured summaries.
    """
    results = []

    for event in events:
        if event.event_type == "deleted":
            # Need repo_id - get from existing file record or derive
            repo_id = f"repo:{repo_root.name}"
            summary = handle_deleted_file(conn, repo_id, event.repo_relative_path)
        else:
            # Created or modified
            summary = reindex_changed_file(conn, repo_root, event.absolute_path, config)

        results.append(summary)

    return results
