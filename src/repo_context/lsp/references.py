"""LSP reference enrichment orchestrator."""

import json
from datetime import datetime, timezone
from pathlib import Path

from repo_context.graph.references import build_reference_stats
from repo_context.lsp.protocol import normalize_location
from repo_context.lsp.resolver import get_reference_query_position, resolve_file_by_uri
from repo_context.lsp.mapper import pick_smallest_containing_symbol, find_module_node_for_file


# Confidence levels
CONFIDENCE_EXACT = 0.9
CONFIDENCE_MODULE = 0.7


def build_reference_edge(
    repo_id: str,
    from_id: str,
    to_id: str,
    confidence: float,
    evidence_file_id: str,
    evidence_uri: str,
    evidence_range_json: dict,
    payload_json: dict,
) -> dict:
    """Build a references edge dict.

    Edge ID format: edge:{repo_id}:references:{from_id}->{to_id}:{line}:{character}
    """
    start = evidence_range_json["start"]
    edge_id = f"edge:{repo_id}:references:{from_id}->{to_id}:{start['line']}:{start['character']}"
    return {
        "id": edge_id,
        "repo_id": repo_id,
        "kind": "references",
        "from_id": from_id,
        "to_id": to_id,
        "source": "lsp",
        "confidence": confidence,
        "evidence_file_id": evidence_file_id,
        "evidence_uri": evidence_uri,
        "evidence_range_json": evidence_range_json,
        "payload_json": payload_json,
        "last_indexed_at": datetime.now(timezone.utc).isoformat(),
    }


def load_symbols_for_file(conn, file_id: str):
    """Load all symbols for a file.

    Args:
        conn: SQLite connection.
        file_id: File ID to load symbols for.

    Returns:
        List of symbol dicts.
    """
    cursor = conn.execute(
        "SELECT * FROM nodes WHERE file_id = ?",
        (file_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def replace_reference_edges_for_target(conn, target_symbol_id: str, edges: list, refresh_metadata: dict):
    """Replace all reference edges for a target symbol transactionally.

    Args:
        conn: SQLite connection.
        target_symbol_id: Target symbol ID.
        edges: New reference edges to insert.
        refresh_metadata: Metadata for refresh tracking.
    """
    try:
        conn.execute("BEGIN")
        conn.execute(
            "DELETE FROM edges WHERE kind = 'references' AND to_id = ?",
            (target_symbol_id,),
        )

        for edge in edges:
            conn.execute(
                """
                INSERT INTO edges (
                    id, repo_id, kind, from_id, to_id, source, confidence,
                    evidence_file_id, evidence_uri, evidence_range_json, payload_json, last_indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge["id"],
                    edge["repo_id"],
                    edge["kind"],
                    edge["from_id"],
                    edge["to_id"],
                    edge["source"],
                    edge["confidence"],
                    edge["evidence_file_id"],
                    edge["evidence_uri"],
                    json.dumps(edge["evidence_range_json"]),
                    json.dumps(edge["payload_json"]),
                    edge["last_indexed_at"],
                ),
            )

        conn.execute(
            """
            INSERT INTO reference_refresh (
                target_symbol_id, available, last_refreshed_at, refresh_status, error_code
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(target_symbol_id) DO UPDATE SET
                available = excluded.available,
                last_refreshed_at = excluded.last_refreshed_at,
                refresh_status = excluded.refresh_status,
                error_code = excluded.error_code
            """,
            (
                refresh_metadata["target_symbol_id"],
                refresh_metadata["available"],
                refresh_metadata["last_refreshed_at"],
                refresh_metadata.get("refresh_status"),
                refresh_metadata.get("error_code"),
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def enrich_references_for_symbol(conn, lsp_client, target_symbol, open_all_files: bool = True):
    """Enrich references for a single target symbol.

    Args:
        conn: SQLite connection.
        lsp_client: PyrightLspClient instance.
        target_symbol: Target symbol dict with keys: id, repo_id, file_id, file_path, uri, qualified_name, kind, scope, range_json, selection_range_json, repo_root.
        open_all_files: If True (default), open all tracked .py files before requesting for better cross-file detection.

    Returns:
        Reference stats dict from build_reference_stats.
    """
    # Step 1: Resolve query position
    position = get_reference_query_position(target_symbol)

    # Step 2: Ensure client started
    repo_root = target_symbol.get("repo_root", str(Path.cwd()))
    lsp_client.start(repo_root)

    # Step 3: Open target file
    target_path = Path(target_symbol["file_path"])
    target_text = target_path.read_text(encoding="utf-8")
    lsp_client.did_open(target_symbol["uri"], target_text)

    # Step 4: Optionally open all tracked .py files
    if open_all_files:
        rows = conn.execute("SELECT file_path, uri FROM files WHERE file_path LIKE '%.py'").fetchall()
        for row in rows:
            path = Path(row[0])
            uri = row[1]
            if not path.exists() or str(path) == str(target_path):
                continue
            lsp_client.did_open(uri, path.read_text(encoding="utf-8"))

    # Step 5: Request references
    locations = lsp_client.find_references(
        target_symbol["uri"],
        position["line"],
        position["character"],
        include_declaration=False,
    ) or []

    # Steps 6-14: Map locations to symbols and build edges
    edges = []
    seen = set()

    for loc in locations:
        normalized = normalize_location(loc)
        file_row = resolve_file_by_uri(conn, normalized["uri"])
        if not file_row:
            continue

        symbols = load_symbols_for_file(conn, file_row["id"])
        source_symbol = pick_smallest_containing_symbol(symbols, normalized["range"])
        mapping_mode = "exact_symbol"
        confidence = CONFIDENCE_EXACT

        if source_symbol is None:
            source_symbol = find_module_node_for_file(symbols)
            mapping_mode = "module_fallback"
            confidence = CONFIDENCE_MODULE

        if source_symbol is None:
            continue

        # Step 14: Deduplicate
        dedupe_key = (
            target_symbol["id"],
            source_symbol["id"],
            normalized["uri"],
            normalized["range"]["start"]["line"],
            normalized["range"]["start"]["character"],
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        # Step 13: Build edge
        edge = build_reference_edge(
            repo_id=target_symbol["repo_id"],
            from_id=source_symbol["id"],
            to_id=target_symbol["id"],
            confidence=confidence,
            evidence_file_id=file_row["id"],
            evidence_uri=normalized["uri"],
            evidence_range_json=normalized["range"],
            payload_json={
                "mapping_mode": mapping_mode,
                "target_symbol_kind": target_symbol["kind"],
                "source_symbol_kind": source_symbol["kind"],
                "source_symbol_scope": source_symbol.get("scope"),
            },
        )
        edges.append(edge)

    # Steps 15-16: Replace edges and mark refresh
    refresh_metadata = {
        "target_symbol_id": target_symbol["id"],
        "available": True,
        "last_refreshed_at": datetime.now(timezone.utc).isoformat(),
        "refresh_status": "ok",
        "error_code": None,
    }

    replace_reference_edges_for_target(conn, target_symbol["id"], edges, refresh_metadata)

    # Step 17: Return stats
    return build_reference_stats(conn, target_symbol["id"])
