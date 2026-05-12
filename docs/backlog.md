# Post-MVP Backlog

## Tier 1 — first real users
- [ ] Real WhatsApp Business API
- [ ] Live-mode Razorpay (after legal review)
- [ ] Multi-currency
- [ ] Email/SMS notifications
- [ ] Merchant KYC (Aadhaar/PAN)
- [ ] LLM cost optimization
- [ ] Real merchant onboarding flow with vision
- [ ] Buyer dashboard (currently MCP-only)
- [ ] Merchant dashboard (currently SQL-only)

## Tier 1.2 — API gaps surfaced by 1.9 demo script
- [x] `GET /commerce/session/{id}` enriched with flat replay + receipt fields
  (folded into 2.7, shipped 2026-05-12).
- [x] `GET /agents/{id}/pubkey` (folded into 2.6, shipped 2026-05-12).

## Tier 1.3 — code-review findings from 2.4–2.9 batch (2026-05-12)

Fixed before push:
- [x] Platform key DB storage violated CLAUDE.md rule 7 — switched to
  env-or-ephemeral module-cached keypair, dropped `PlatformKey` model +
  migration (B2).
- [x] `/.well-known/platform-pubkey` mutating GET handler — converted to
  read-only, key loaded once at lifespan startup (B1).
- [x] `run_auction` was calling `validate_spend` without `daily_spent`, so
  the daily cap was unenforced for auction endpoints — now threaded
  through from `/commerce/auction` (B3).
- [x] MCP `negotiate` random Idempotency-Key — now deterministic
  SHA-256(canonical inputs) so retries hit the cache (M4).
- [x] MCP module docstring lied about private-key egress — corrected to
  state buyer key IS sent over loopback to backend (M5).

Deferred (still open):
- [ ] **Unauthenticated `GET /commerce/session/{id}` leaks LLM prompts**
  (full buyer priorities + budget) via `replay_data`. Acceptable for MVP
  with one demo agent; gate behind buyer-agent auth before any
  multi-tenant deployment. (M1)
- [ ] **MCP buyer private key over loopback HTTP**. Works only because MCP
  + backend are co-deployed. Refactor backend to a proof-of-possession
  nonce flow (sign a server-issued challenge) before cross-host deploy.
- [ ] **`replay_prompt_hash` column never populated** — defeats ADR-007
  tamper-evidence. Compute `sha256(canonical(replay_payload))` on persist. (Mi2)
- [ ] **`idempotency_keys` 24h pending rows are sticky** — a crashed
  worker between claim + finalize blocks retries for a day. Add TTL
  check inside `_idempotency_replay_or_409` to expire stale claims. (M5/review)
- [ ] **`/agents/{id}/pubkey` is an existence oracle for `did:merchant:*`**.
  Soft info leak. Add uniform 404s or auth before hardening. (M6)
- [ ] **Auction round shape audit coverage**. `save_session_and_audit`
  synthesises `rounds[0] = {type: "auction", ...}`; verify
  `build_audit_log` doesn't silently no-op for that shape. (M7)
- [ ] **`verify_receipt` raises RuntimeError on bad input** instead of
  returning a `{verified: false, reason}` shape like the other tools. (Mi4)
- [ ] **`replay_negotiation` returns `match: false` for empty details**
  instead of `match: null` + explanation. (Mi5)
- [ ] **Mid-function imports** in `main.py` (the old `_os`/`_ed`/`_ser`)
  cleaned up when B1 landed; flag in future review.

## Tier 1.5 — schema items deferred from 1.2
- [ ] `negotiation_sessions.approval_status` + `approved_at` + `approved_by` —
  buyer-approval gate before settlement. Deferred because MCP-first flow
  has no separate approval step in the MVP. Add when web-first flow lands.
- [ ] Swap `products.embedding` JSONB → `pgvector` `vector(1536)` once
  embedding count crosses ~10k or matcher latency exceeds 50ms.

## Tier 2 — product polish
- [ ] Sandboxed custom agent skills
- [ ] Skill marketplace
- [ ] Agent memory across sessions
- [ ] Multi-language (Hindi, Marathi, Tamil)
- [ ] Mobile native app
- [ ] Buyer/merchant rating
- [ ] Dispute resolution flow

## Tier 3 — scale + infra
- [ ] Dedicated infra (off Render)
- [ ] Postgres read replicas
- [ ] Redis for sessions + WebSocket pub/sub
- [ ] Background queue (Arq/Celery)
- [ ] OpenTelemetry, Grafana

## Tier 4 — protocol
- [ ] W3C Verifiable Credential format
- [ ] Public protocol spec
- [ ] SDK in Go and TypeScript
- [ ] Federation across platforms

## Ideas to evaluate
- [ ] Group buying
- [ ] Reverse auction
- [ ] Subscription negotiation
