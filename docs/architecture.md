# Architecture

## High-level

Single FastAPI backend orchestrates everything. Two entry points to the same backend:
- Web dashboard (React + Vite)
- MCP server (separate Python service exposing tools to Claude/ChatGPT)

```
[ Claude / ChatGPT ]  [ Web Dashboard ]
        |                    |
        v                    v
   [ MCP Server ]------>[ FastAPI ]
                              |
                              v
   [ Postgres ]   [ OpenAI ]   [ Razorpay ]
```

## Backend layout (backend/app/)

Strict layering. Imports go one direction: domain → adapters → api.

**app/domain/** — pure logic, no framework imports
- identity.py — Ed25519 keygen, policy signing, credential creation
- negotiation.py — round-by-round negotiation with LLM + math clamps
- auction.py — multi-merchant auction
- matcher.py — semantic + location + price filter
- policy.py — spend validation
- receipts.py — signed transaction receipts

**app/adapters/** — IO and external services
- db/ — SQLAlchemy models, repositories
- llm/ — OpenAI client wrapper
- razorpay/ — order create, webhook verify
- embeddings/ — embedding cache + similarity search

**app/api/** — FastAPI routes
- routes/agents.py
- routes/commerce.py
- routes/sessions.py
- routes/verify.py
- routes/webhooks.py
- ws/ — WebSocket handlers

## MCP server (mcp_server/)

Separate Python process. Calls backend HTTP API. Tools:
- search_local_merchants(product, location, max_price, radius_km)
- negotiate(product_id, max_price, skill)
- verify_receipt(receipt_json)
- get_audit_trail(session_id)
- replay_negotiation(session_id)

## Database tables

- agents — DID + Ed25519 public key + owner_id
- spending_policies — signed delegation, links to agent
- merchants — human merchants
- products — what merchants list
- merchant_agents — one per product, links product to negotiating agent
- buyers — human buyers
- agent_skills — 6 persona presets
- match_requests — buyer queries
- negotiation_sessions — auction/negotiation runs (includes replay_data JSON)
- signed_receipts — settlement receipts with Ed25519 signatures
- audit_log — every state change

See migrations/ for schema.

## Critical invariants

1. No LLM math. Prices computed in Python, LLM gets ranges as constraints, output clamped.
2. Idempotent settlement. Retried negotiate must not create duplicate orders.
3. Receipt non-repudiation. Every settled txn signed; signature covers
   (txn_id, session_id, agent_id, policy_id, amount, currency, settled_at).
4. Human approval gate. No money moves without explicit human approval after agents settle.
5. Replay data stored. Every LLM call's prompt + model + temperature + seed saved
   for verifiable replay.

## Data flow: a successful purchase

1. Buyer query (web or MCP)
2. Matcher: location haversine + embedding similarity + price band
3. If 1 match: 1-on-1 negotiation. If 2+: auction.
4. Spawn agents with buyer's signed credential, merchant configs
5. Negotiation runs (rounds streamed via WebSocket)
6. Result saved with status=pending_approval
7. Buyer notified (web push for MVP)
8. Buyer approves → Razorpay order created with idempotency key
9. Buyer pays UPI
10. Webhook verified → mark settled
11. Build signed receipt, write audit log
12. Notify merchant
