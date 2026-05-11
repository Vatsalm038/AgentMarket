"""AgentMarket MCP server (ticket 2.3 scaffold).

Boots fastmcp on $MCP_PORT (default 8001) with a single smoke-test tool that
confirms the MCP server can reach the FastAPI backend over loopback. Real
tools (search_local_merchants, negotiate, verify_receipt, get_audit_trail)
land in 2.4 – 2.7.

Run from repo root:
    /home/vatsal/personal/agent-market/.venv/bin/python -m mcp_server.server

The backend imports below (`models`, `database`) deliberately happen at
module-import time so any ORM / DB-config breakage fails the boot loudly
instead of surfacing on the first tool call.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import httpx
from fastmcp import FastMCP

# Make the flat-layout backend importable so we fail loud if its models/DB
# config drift. Mirrors the trick used in backend/scripts/*.
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))

# These imports are intentionally unused at scaffold time — they exist to
# trigger import-time validation of the backend's ORM + engine config.
import database  # noqa: F401
import models    # noqa: F401


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MCP_PORT = int(os.getenv("MCP_PORT", "8001"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
VERSION = "0.1.0"

mcp = FastMCP(name="agentmarket-mcp")


@mcp.tool
async def ping() -> dict:
    """Smoke test: confirms this MCP server is reachable and can in turn reach
    the FastAPI backend's /health over loopback. Real tools land in 2.4+."""
    backend_health: dict | str
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{BACKEND_URL}/health")
            r.raise_for_status()
            backend_health = r.json()
        except Exception as exc:  # noqa: BLE001
            # Don't fail the tool — the whole point of ping is to surface the
            # backend's reachability state to the caller.
            backend_health = f"unreachable: {exc.__class__.__name__}: {exc}"

    return {
        "status": "ok",
        "server": "agentmarket-mcp",
        "version": VERSION,
        "backend_health": backend_health,
    }


def main() -> None:
    logger.info("MCP server listening on port %d (backend=%s)", MCP_PORT, BACKEND_URL)
    # Streamable-HTTP transport so the server is reachable over loopback for
    # the smoke test; Claude Desktop / Claude.ai stdio integration plugs in
    # when 2.10 wires this up end-to-end.
    mcp.run(transport="http", host="127.0.0.1", port=MCP_PORT)


if __name__ == "__main__":
    main()
