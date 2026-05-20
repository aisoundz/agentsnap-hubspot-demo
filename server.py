"""AgentSnap HubSpot Demo — MCP server entry point.

A standalone MCP server that lets Claude (or any MCP client) do real
operations work — renewals, invoices, claims, commissions — using HubSpot
as the system of record instead of a traditional AMS.

Two modes:
  - Mock mode (default): rich seed data, zero setup. Ideal for a first look.
  - Live HubSpot mode: set HUBSPOT_PRIVATE_APP_TOKEN env var to point at
    a real HubSpot account.

Run:
    python server.py

Or wire it into Claude Desktop via claude_desktop_config.json (see README).
"""

from mcp.server.fastmcp import FastMCP

import config
from tools import register_tools


def build_server() -> FastMCP:
    server_name = (
        "AgentSnap HubSpot Demo (mock)"
        if config.HUBSPOT_MODE == "mock"
        else "AgentSnap HubSpot Demo (live)"
    )
    mcp = FastMCP(server_name)
    register_tools(mcp)
    return mcp


mcp = build_server()


if __name__ == "__main__":
    mcp.run()
