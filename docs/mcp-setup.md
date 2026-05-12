# MCP setup (Day 2 ticket 2.10)

How to run the AgentMarket MCP server locally and connect it to Claude.ai
(or any MCP client) for the demo.

## What you get

Six tools exposed to the LLM client:

| Tool | Purpose |
|---|---|
| `ping` | Health probe; returns backend health + demo agent id |
| `search_local_merchants` | Anchor-product search via matcher (haversine + embedding + price band) |
| `negotiate` | Run a multi-merchant auction; returns winner + signed receipt session id |
| `verify_receipt` | Ed25519-verify the receipt for a settled session (uses backend's `/agents/{id}/pubkey`) |
| `get_audit_trail` | One-line summaries of every audit event + receipt summary + replay metadata |
| `replay_negotiation` | Re-run stored LLM prompts with the same seed and compare (ADR-007) |

All six are wired against a **single demo buyer identity** registered at MCP
boot — see "Auth model" below.

## Prerequisites

- Repo cloned and bootstrapped (see [`fresh-laptop-setup.md`](./fresh-laptop-setup.md))
- Postgres running with seed data + product embeddings (`scripts/seed.py`, `scripts/embed_products.py`)
- `OPENAI_API_KEY` exported (auction uses gpt-4o-mini)
- Optional: `PLATFORM_PRIVATE_KEY_B64` set to pin the platform key across restarts

## Start sequence

Two processes, two terminals. Order matters — MCP server probes backend on boot.

```bash
# Terminal 1 — backend (must be cwd=backend/ because imports are flat)
cd /path/to/agent-market/backend
../.venv/bin/uvicorn main:app --port 8000 --host 127.0.0.1

# Terminal 2 — MCP server (repo root)
cd /path/to/agent-market
.venv/bin/python -m mcp_server.server
```

Backend log should show `Uvicorn running on http://127.0.0.1:8000`. MCP log
should show `Uvicorn running on http://127.0.0.1:8001` and the FastMCP banner.

Sanity check:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/.well-known/platform-pubkey
```

## Verify via `ping` (fastmcp client)

The MCP server speaks streamable HTTP at `/mcp`. Quickest local probe:

```bash
.venv/bin/python - <<'PY'
import asyncio, json
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8001/mcp") as c:
        tools = await c.list_tools()
        print("tools:", [t.name for t in tools])
        r = await c.call_tool("ping", {})
        print(json.dumps(r.data, indent=2, default=str))

asyncio.run(main())
PY
```

Expected output: 6 tool names + `{"status": "ok", "backend_health": ..., "demo_agent_id": <didagent...>}`.

## Connect Claude.ai (custom MCP connector)

Claude.ai's hosted UI cannot reach `localhost` on your laptop. You need to
tunnel the MCP port to a public HTTPS URL.

### Option A — cloudflared (free, persistent)

```bash
cloudflared tunnel --url http://127.0.0.1:8001
# Copy the printed https://<random>.trycloudflare.com URL.
```

### Option B — ngrok

```bash
ngrok http 8001
# Use the https forwarding URL.
```

### Add to Claude.ai

1. Open Claude.ai → Settings → Connectors → Add custom connector.
2. Name: `agentmarket-local`
3. URL: `https://<your-tunnel-host>/mcp`
4. Transport: streamable HTTP (default).
5. Save. Claude should list 6 tools.

Run a `ping` from a new chat. If it returns `demo_agent_id`, you're live.

## Auth model (read before the demo)

- MCP server registers ONE demo buyer agent against `/agents/register` on
  first non-`ping` tool call.
- The private key lives in **process memory only** — never logged, never
  returned to Claude, never persisted.
- It IS sent to the colocated backend over loopback HTTP inside `negotiate()`
  because the backend signs settle-time receipts with it. This is acceptable
  *only* because backend and MCP server are co-deployed; cross-host
  deployments need a proof-of-possession nonce flow (see backlog).
- Restart MCP → fresh agent, fresh policy, no shared history.

## Demo script (6 prompts for the video)

1. "What can you do?" → Claude lists the tools.
2. "Find me a canvas wallet under ₹2000 near Mumbai." → `search_local_merchants`.
3. "Negotiate the best deal for that first result, lowest price please." → `negotiate`.
4. "Verify the receipt for that session." → `verify_receipt` (expect `verified: true`).
5. "Show me the audit trail for that session." → `get_audit_trail`.
6. "Replay that negotiation — did the LLM produce the same quotes?" → `replay_negotiation`.

Watch the backend log alongside — every state mutation hits `audit_log`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'auction'` on uvicorn boot | Started uvicorn from repo root | `cd backend/` first; imports are flat |
| `ping` returns `backend_health: {error: ...}` | Backend not up yet | Start backend first, give it ~2s |
| `negotiate` returns `policy_blocked` with "max_price_inr below cap" | Per-txn cap on demo policy is fixed at boot | Omit `max_price_inr` or pass a value ≥ demo cap |
| `verify_receipt` returns `verified: false` | Payload was modified after signing, or wrong agent pubkey | Compare `canonical_bytes` between sign + verify paths |
| `replay_negotiation` reports `match: false` for some quotes | OpenAI `seed` is best-effort; drift happens | Expected — ADR-007 reports honestly rather than hiding |
| MCP boot hangs at "Registering demo agent" | OPENAI_API_KEY missing or backend unreachable | Export the key, confirm `curl :8000/health` works |
| Claude.ai connector shows 0 tools | Tunnel URL missing `/mcp` suffix | Append `/mcp` to the public URL |

## Files involved

- `mcp_server/server.py` — all six tools, demo identity, fastmcp boot
- `backend/main.py` — `/commerce/auction`, `/agents/{id}/pubkey`, `/commerce/session/{id}`, `/.well-known/platform-pubkey`
- `backend/auction.py` — auction engine + replay capture
- `backend/matcher.py` — anchor search (haversine + embeddings + price band)
