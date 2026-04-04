"""MCP server package.

Exposes the repository graph, symbol context, reference data, and risk engine
through a deterministic MCP server with strict tool contracts.
"""

from repo_context.mcp.server import create_server, run_server

__all__ = ["create_server", "run_server"]
