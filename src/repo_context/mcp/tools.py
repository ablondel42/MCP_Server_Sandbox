"""MCP tool handlers.

Implements all 6 MCP tools with strict input validation and structured output.
"""

import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from repo_context.config import get_config
from repo_context.storage import (
    get_connection,
    close_connection,
    initialize_database,
    get_node_by_id,
    get_node_by_qualified_name,
)
from repo_context.storage.files import get_file_by_id
from repo_context.graph import (
    find_symbols_by_name,
    build_reference_stats,
    list_reference_edges_for_target,
    analyze_symbol_risk as engine_analyze_symbol_risk,
    analyze_target_set_risk as engine_analyze_target_set_risk,
)
from repo_context.context import build_symbol_context
from repo_context.mcp.schemas import (
    ResolveSymbolInput,
    GetSymbolContextInput,
    RefreshSymbolReferencesInput,
    GetSymbolReferencesInput,
    AnalyzeSymbolRiskInput,
    AnalyzeTargetSetRiskInput,
)
from repo_context.mcp.errors import (
    error_result,
    success_result,
    ERROR_INVALID_INPUT,
    ERROR_SYMBOL_NOT_FOUND,
    ERROR_AMBIGUOUS_SYMBOL,
    ERROR_REFERENCES_UNAVAILABLE,
    ERROR_LSP_FAILURE,
    ERROR_INTERNAL_ERROR,
)
from repo_context.mcp.adapters import adapt_node, adapt_edge, adapt_context, adapt_risk_result


def _log(message: str) -> None:
    """Log to stderr (safe for STDIO transport)."""
    print(message, file=sys.stderr)


def _get_conn(db_path: str | None = None):
    """Get database connection, initializing if needed."""
    config = get_config()
    db = db_path or config.db_path
    conn = get_connection(db)
    initialize_database(conn)
    return conn


async def resolve_symbol(
    repo_id: str,
    qualified_name: str,
    kind: str | None = None,
    file_id: str | None = None,
    db_path: str | None = None,
) -> str:
    """Resolve a symbol by repo ID and qualified name."""
    try:
        inp = ResolveSymbolInput(
            repo_id=repo_id,
            qualified_name=qualified_name,
            kind=kind,
            file_id=file_id,
        )
    except Exception as e:
        return json.dumps(error_result(ERROR_INVALID_INPUT, str(e)))

    conn = _get_conn(db_path)
    try:
        symbol = get_node_by_qualified_name(conn, inp.repo_id, inp.qualified_name)

        if symbol is not None:
            if inp.kind and symbol["kind"] != inp.kind:
                symbol = None
            if inp.file_id and symbol and symbol["file_id"] != inp.file_id:
                symbol = None

        if symbol is not None:
            return json.dumps(success_result({"symbol": adapt_node(symbol)}))

        pattern = f"%{inp.qualified_name}%"
        candidates = find_symbols_by_name(conn, inp.repo_id, pattern, kind=inp.kind)

        if inp.file_id:
            candidates = [c for c in candidates if c.get("file_id") == inp.file_id]

        if not candidates:
            return json.dumps(error_result(ERROR_SYMBOL_NOT_FOUND, f"Symbol not found: {inp.qualified_name}"))

        if len(candidates) > 1:
            return json.dumps(error_result(
                ERROR_AMBIGUOUS_SYMBOL,
                f"Ambiguous symbol: {inp.qualified_name}",
                details={
                    "candidates": [
                        {"id": c["id"], "kind": c["kind"], "file_id": c["file_id"], "qualified_name": c["qualified_name"]}
                        for c in candidates
                    ]
                },
            ))

        return json.dumps(success_result({"symbol": adapt_node(candidates[0])}))
    except Exception as e:
        _log(f"resolve_symbol error: {e}")
        return json.dumps(error_result(ERROR_INTERNAL_ERROR, str(e)))
    finally:
        close_connection(conn)


async def get_symbol_context(symbol_id: str, db_path: str | None = None) -> str:
    """Get full context for a symbol."""
    try:
        inp = GetSymbolContextInput(symbol_id=symbol_id)
    except Exception as e:
        return json.dumps(error_result(ERROR_INVALID_INPUT, str(e)))

    conn = _get_conn(db_path)
    try:
        symbol = get_node_by_id(conn, inp.symbol_id)
        if symbol is None:
            return json.dumps(error_result(ERROR_SYMBOL_NOT_FOUND, f"Symbol not found: {inp.symbol_id}"))

        ctx = build_symbol_context(conn, inp.symbol_id)
        if ctx is None:
            return json.dumps(error_result(ERROR_SYMBOL_NOT_FOUND, f"Could not build context for: {inp.symbol_id}"))

        return json.dumps(success_result({"context": adapt_context(ctx)}))
    except Exception as e:
        _log(f"get_symbol_context error: {e}")
        return json.dumps(error_result(ERROR_INTERNAL_ERROR, str(e)))
    finally:
        close_connection(conn)


async def refresh_symbol_references(symbol_id: str, db_path: str | None = None) -> str:
    """Refresh LSP references for a symbol."""
    try:
        inp = RefreshSymbolReferencesInput(symbol_id=symbol_id)
    except Exception as e:
        return json.dumps(error_result(ERROR_INVALID_INPUT, str(e)))

    conn = _get_conn(db_path)
    try:
        symbol = get_node_by_id(conn, inp.symbol_id)
        if symbol is None:
            return json.dumps(error_result(ERROR_SYMBOL_NOT_FOUND, f"Symbol not found: {inp.symbol_id}"))

        file_record = get_file_by_id(conn, symbol["file_id"])
        if file_record is None:
            return json.dumps(error_result(ERROR_REFERENCES_UNAVAILABLE, f"File not found for symbol: {symbol['file_id']}"))

        payload = json.loads(symbol.get("payload_json", "{}")) if symbol.get("payload_json") else {}
        target_symbol = {
            "id": symbol["id"],
            "repo_id": symbol["repo_id"],
            "file_id": symbol["file_id"],
            "file_path": file_record["file_path"],
            "uri": symbol["uri"],
            "qualified_name": symbol["qualified_name"],
            "kind": symbol["kind"],
            "scope": symbol.get("scope"),
            "range_json": symbol.get("range_json"),
            "selection_range_json": symbol.get("selection_range_json"),
            "repo_root": str(Path.cwd()),
        }

        try:
            from repo_context.lsp import PyrightLspClient
            from repo_context.lsp.references import enrich_references_for_symbol

            with PyrightLspClient() as client:
                stats = enrich_references_for_symbol(conn, client, target_symbol, open_all_files=True)
        except FileNotFoundError:
            return json.dumps(error_result(ERROR_LSP_FAILURE, "LSP server (pyright) not found"))
        except Exception as e:
            _log(f"LSP refresh failed: {e}")
            return json.dumps(error_result(ERROR_LSP_FAILURE, str(e)))

        return json.dumps(success_result({"symbol_id": inp.symbol_id, "reference_summary": stats}))
    except Exception as e:
        _log(f"refresh_symbol_references error: {e}")
        return json.dumps(error_result(ERROR_INTERNAL_ERROR, str(e)))
    finally:
        close_connection(conn)


async def get_symbol_references(symbol_id: str, db_path: str | None = None) -> str:
    """Get stored references for a symbol (read-only)."""
    try:
        inp = GetSymbolReferencesInput(symbol_id=symbol_id)
    except Exception as e:
        return json.dumps(error_result(ERROR_INVALID_INPUT, str(e)))

    conn = _get_conn(db_path)
    try:
        symbol = get_node_by_id(conn, inp.symbol_id)
        if symbol is None:
            return json.dumps(error_result(ERROR_SYMBOL_NOT_FOUND, f"Symbol not found: {inp.symbol_id}"))

        edges = list_reference_edges_for_target(conn, inp.symbol_id)
        stats = build_reference_stats(conn, inp.symbol_id)

        return json.dumps(success_result({
            "symbol_id": inp.symbol_id,
            "references": [adapt_edge(e) for e in edges],
            "reference_summary": stats,
        }))
    except Exception as e:
        _log(f"get_symbol_references error: {e}")
        return json.dumps(error_result(ERROR_INTERNAL_ERROR, str(e)))
    finally:
        close_connection(conn)


async def analyze_symbol_risk(symbol_id: str, db_path: str | None = None) -> str:
    """Analyze risk for a single symbol."""
    try:
        inp = AnalyzeSymbolRiskInput(symbol_id=symbol_id)
    except Exception as e:
        return json.dumps(error_result(ERROR_INVALID_INPUT, str(e)))

    conn = _get_conn(db_path)
    try:
        symbol = get_node_by_id(conn, inp.symbol_id)
        if symbol is None:
            return json.dumps(error_result(ERROR_SYMBOL_NOT_FOUND, f"Symbol not found: {inp.symbol_id}"))

        result = engine_analyze_symbol_risk(conn, inp.symbol_id)
        return json.dumps(success_result({"risk": adapt_risk_result(result)}))
    except Exception as e:
        _log(f"analyze_symbol_risk error: {e}")
        return json.dumps(error_result(ERROR_INTERNAL_ERROR, str(e)))
    finally:
        close_connection(conn)


async def analyze_target_set_risk(symbol_ids: list[str], db_path: str | None = None) -> str:
    """Analyze risk for a set of symbols."""
    try:
        inp = AnalyzeTargetSetRiskInput(symbol_ids=symbol_ids)
    except Exception as e:
        return json.dumps(error_result(ERROR_INVALID_INPUT, str(e)))

    conn = _get_conn(db_path)
    try:
        for sid in inp.symbol_ids:
            symbol = get_node_by_id(conn, sid)
            if symbol is None:
                return json.dumps(error_result(ERROR_SYMBOL_NOT_FOUND, f"Symbol not found: {sid}"))

        result = engine_analyze_target_set_risk(conn, inp.symbol_ids)
        return json.dumps(success_result({"risk": adapt_risk_result(result)}))
    except Exception as e:
        _log(f"analyze_target_set_risk error: {e}")
        return json.dumps(error_result(ERROR_INTERNAL_ERROR, str(e)))
    finally:
        close_connection(conn)


def register_tools(mcp: FastMCP, db_path: str | None = None) -> None:
    """Register all MCP tools on the given FastMCP server."""

    @mcp.tool()
    async def resolve_symbol_tool(
        repo_id: str,
        qualified_name: str,
        kind: str | None = None,
        file_id: str | None = None,
    ) -> str:
        """Resolve a symbol by repo ID and qualified name.

        Args:
            repo_id: Repository ID (e.g., "repo:MyProject").
            qualified_name: Fully qualified symbol name.
            kind: Optional symbol kind filter.
            file_id: Optional file ID for narrowing.
        """
        return await resolve_symbol(repo_id, qualified_name, kind, file_id, db_path=db_path)

    @mcp.tool()
    async def get_symbol_context_tool(symbol_id: str) -> str:
        """Get full context for a symbol including relationships and references.

        Args:
            symbol_id: Full symbol ID.
        """
        return await get_symbol_context(symbol_id, db_path=db_path)

    @mcp.tool()
    async def refresh_symbol_references_tool(symbol_id: str) -> str:
        """Refresh LSP references for a symbol.

        Args:
            symbol_id: Full symbol ID to refresh.
        """
        return await refresh_symbol_references(symbol_id, db_path=db_path)

    @mcp.tool()
    async def get_symbol_references_tool(symbol_id: str) -> str:
        """Get stored references for a symbol (read-only, no auto-refresh).

        Args:
            symbol_id: Full symbol ID.
        """
        return await get_symbol_references(symbol_id, db_path=db_path)

    @mcp.tool()
    async def analyze_symbol_risk_tool(symbol_id: str) -> str:
        """Analyze risk for a single symbol.

        Args:
            symbol_id: Full symbol ID.
        """
        return await analyze_symbol_risk(symbol_id, db_path=db_path)

    @mcp.tool()
    async def analyze_target_set_risk_tool(symbol_ids: list[str]) -> str:
        """Analyze risk for a set of symbols.

        Args:
            symbol_ids: List of symbol IDs to analyze.
        """
        return await analyze_target_set_risk(symbol_ids, db_path=db_path)
