"""MCP server wiring.

Initializes config, registers tools, and starts serving.
"""

import sys

from mcp.server.fastmcp import FastMCP

from repo_context.mcp.tools import register_tools


def create_server(db_path: str | None = None, debug: bool = False) -> FastMCP:
    """Create and configure the MCP server.

    Args:
        db_path: Optional path to database file.
        debug: Enable debug logging.

    Returns:
        Configured FastMCP server instance.
    """
    mcp = FastMCP("repo-context")

    # Register all tools
    register_tools(mcp, db_path=db_path)

    if debug:
        print("MCP server created with tools: resolve_symbol, get_symbol_context, "
              "refresh_symbol_references, get_symbol_references, analyze_symbol_risk, "
              "analyze_target_set_risk", file=sys.stderr)

    return mcp


def run_server(db_path: str | None = None, debug: bool = False) -> None:
    """Start the MCP server on stdio transport.

    Args:
        db_path: Optional path to database file.
        debug: Enable debug logging.
    """
    mcp = create_server(db_path=db_path, debug=debug)
    print(f"Starting MCP server on stdio (db_path={db_path or 'default'})", file=sys.stderr)
    mcp.run(transport="stdio")
