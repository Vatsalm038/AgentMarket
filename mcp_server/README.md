# AgentMarket MCP Server

Thin fastmcp shell that exposes AgentMarket's commerce flow as MCP tools.
Ticket 2.3 ships a scaffold with one smoke-test tool (`ping`); real tools
arrive in 2.4 – 2.7.

## Run locally

```
/home/vatsal/personal/agent-market/.venv/bin/python -m mcp_server.server
```

Defaults to port 8001. Override with `MCP_PORT=...`. The server expects the
FastAPI backend to be reachable at `http://localhost:8000` (override with
`BACKEND_URL=...`).

`OPENAI_API_KEY` must be set in the environment: this process transitively
imports backend modules (matcher, auction) that initialise the OpenAI client
on first use.

## Claude.ai / Claude Desktop

Claude.ai-compatible via stdio. Wiring instructions land alongside ticket
2.10 once the real tool surface is in place.

## Smoke test

```
curl -N -H 'Accept: text/event-stream' \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"ping","arguments":{}}}' \
  http://127.0.0.1:8001/mcp/
```
