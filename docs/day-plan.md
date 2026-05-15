# 5-Working-Day MVP Plan (~3 calendar weeks at 2hr weekdays + 6hr weekends)

## Calendar mapping

| Calendar Day | Plan Day | Hours | Tickets |
|---|---|---|---|
| Sat W1 | Day 1 part 1 | 6h | 1.1 - 1.6 |
| Sun W1 | Day 1 part 2 + Day 2 start | 6h | 1.7 - 1.9, 2.1 - 2.2 |
| Mon-Fri W2 | Day 2 rest | 10h | 2.3 - 2.10 |
| Sat W2 | Day 3 part 1 | 6h | 3.1 - 3.4 |
| Sun W2 | Day 3 part 2 | 6h | 3.5 - 3.8 |
| Mon-Wed W3 | Day 4 | 6h | 4.1 - 4.4 |
| Thu-Fri W3 | Day 4 finish + Day 5 start | 4h | 4.5 - 4.7, 5.1 - 5.2 |
| Sat W3 | Day 5 deploy + video | 6h | 5.3 - 5.8 |
| Sun W3 | Day 5 launch | 6h | 5.9 - 5.12 |

Total: ~50 hours over ~16 calendar days. Ship by end of Sunday W3.

---

## Day 1 — Foundation + Spine

- [x] 1.1 Restructure repo (backend/, mcp_server/, frontend/, docs/, .claude/) — 30m
- [x] 1.2 Schema migration: drop old, add merchants/products/merchant_agents/agent_skills/signed_receipts. Fix FK drift. — 60m (~75m actual; +idempotency_keys table, signed_payload columns, replay flat columns)
- [x] 1.3 RSA → Ed25519 in identity.py + settlement.py — 45m (tests green; merchant DID generator added per ADR-010)
- [x] 1.4 Fix policy_id linkage in receipts — 20m (credential carries policy_id; receipt signature commits to the real spending_policies row)
- [x] 1.5 Add idempotency keys to settlement — 45m (expanded: full models.py rewrite to mirror migration, signed_receipts persistence, create_transaction returns (payload, signed_bytes), Idempotency-Key header on /commerce/negotiate + /commerce/auction)
- [x] 1.6 Seed 20 Mumbai merchants × ~40 products with realistic INR floor prices — 60m (20 merchants × 30-50 products = 669 rows; idempotent via ON CONFLICT DO NOTHING; price helper unit-tested)
- [x] 1.7 Refactor auction.py to read merchants/products from DB — 60m (ADR-011: async run_auction(db, anchor_product_id, ...); shortlist by category+active ordered by floor_price; real floor_price clamp; bound skill_id per merchant_agent; temperature=0 + per-(auction,merchant) seed for replay; AuctionRequest swapped to anchor_product_id; placeholder fixtures dropped from auction path; folded merchant_agents seed into scripts/seed.py)
- [x] 1.8 Seed 6 agent skills (personas) — 30m (6 rows in agent_skills; deterministic IDs; prompts parameterized by {role} with explicit price-band clamps + JSON contract; idempotent)
- [x] 1.9 End-to-end script scripts/demo_endtoend.py — 90m (HTTP-only demo + smoke test against local uvicorn; deterministic anchor prod_merch_003_09 Canvas Wallet/Andheri; verifies receipt Ed25519 sig client-side using public key captured at /agents/register; idempotency replay byte-identical; replay fields read from audit_log)
## Day 2 — Matcher + MCP

- [x] 2.1 Matcher: haversine + embeddings + price band — 90m (backend/matcher.py + alembic a1b2c3d4e5f6 composite index; 7 new tests; pure _haversine_km + _score helpers; MatcherEmbeddingError on OpenAI failure; warn-log skipped rows with stale/null embeddings)
- [x] 2.2 Pre-compute product embeddings — 20m (backend/scripts/embed_products.py; 669/669 embedded, 0 failed, 22853 tokens, ~$0.0005; idempotent re-run is a no-op; per-batch commit)
- [x] 2.3 MCP server scaffold (fastmcp, port 8001) — 45m (mcp_server/server.py + README; one ping tool; smoke-tested with backend up — backend_health nested in response; pip-upgrade: fastapi 0.115→0.136 to absorb starlette 1.0 brought in by fastmcp 3.2.4)
- [x] 2.4 MCP tool: search_local_merchants — 45m (wraps matcher.shortlist_anchors; reshaped for human-readable output)
- [x] 2.5 MCP tool: negotiate — 90m (MCP-held demo buyer; deterministic idem key from canonical inputs)
- [x] 2.6 MCP tool: verify_receipt — 45m (folded backlog Tier 1.2 — GET /agents/{id}/pubkey shipped on backend)
- [x] 2.7 MCP tool: get_audit_trail — 30m (folded backlog Tier 1.2 — GET /commerce/session/{id} now surfaces signed_receipt + winner_skill_id + llm_seed + replay_data at top level)
- [x] 2.8 /well-known/platform-pubkey endpoint — 15m (env-or-ephemeral module-cached keypair after code review B1/B2; no DB storage)
- [x] 2.9 Verifiable replay: store prompts + seed in replay_data, add replay_negotiation tool — 60m (auction.py captures merchant_quote + buyer_eval prompts; MCP replay_negotiation re-runs and compares honestly)
- [x] 2.10 docs/mcp-setup.md + fresh-laptop-setup.md + live MCP smoke test — 60m (all 6 tools verified end-to-end: ping, search, negotiate, idempotency replay, verify_receipt verified=true, audit trail rendering)

**Day 2 closeout (2026-05-12):** code-review pass surfaced 4 blockers (B1 GET-mutates, B2
rule-7 platform key storage, B3 daily-cap bypass on auction, M4 random idem key) — all
fixed before commit. Remaining majors/minors triaged into backlog Tier 1.3. 45/45 tests
passing, live MCP smoke test green. Pushed to GitHub for laptop-transition checkpoint.

## Day 3 — Frontend (Anthropic/bank aesthetic)

- [x] 3.1 Vite + React + TS + Tailwind + shadcn (zinc theme) — 45m
- [x] 3.2 TanStack Query, axios client, types — 30m
- [x] 3.3 Landing page / — 60m
- [x] 3.4 /session/:id (auth + trail + receipt sections) — 210m
- [x] 3.5 /sessions table list — 60m
- [x] 3.6 /replay/:id side-by-side — 90m
- [x] 3.7 /install-mcp copy-paste page — 45m
- [x] 3.8 Empty states, skeletons, error boundaries — 45m

## Day 4 — Razorpay + WebSocket + audit polish

- [x] 4.1 Razorpay test mode integration end-to-end — 90m
- [x] 4.2 Webhook signature verification — 30m
- [x] 4.3 WebSocket /ws/session/:id streaming — 60m
- [x] 4.4 Frontend live updates via WebSocket — 45m
- [x] 4.5 Audit log polish + show-full toggle — 60m
- [x] 4.6 "Download signed receipt" button — 20m
- [x] 4.7 /verify standalone page — 45m

## Day 5 — Auth + schema pivot + deploy (ADR-012: SignedDeals)

> ADR-012 (2026-05-15): Rebrand to SignedDeals. Drop MCP distribution. Add
> `users` table with JWT auth (bcrypt + HS256). Three React surfaces: marketing,
> buyer dashboard, merchant dashboard. Existing Ed25519/DID/auction/receipt
> system unchanged. Razorpay stays test-mode throughout MVP.

- [x] 5.0 ADR-012 implementation — users migration, auth.py, /auth routes, dark-theme frontend, render.yaml rebrand — 60m
- [ ] 5.1 Postgres on Render paid tier — 20m
- [ ] 5.2 Backend on Render (signeddeals-backend) — 30m
- [ ] 5.3 Frontend on Vercel — 20m
- [ ] 5.4 Custom domain + DNS — 30m
- [ ] 5.5 Run migrations + seed in production — 30m
- [ ] 5.6 Smoke test auth + auction endpoints against production — 30m
- [ ] 5.7 Buyer dashboard: /buyer/sessions list + /buyer/session/:id detail — 120m
- [ ] 5.8 Merchant dashboard: /merchant/products list + deal inbox — 90m
- [ ] 5.9 Record 3-min demo video (script in docs/demo-script.md) — 180m
- [ ] 5.10 Edit video — 90m
- [ ] 5.11 README rewrite with embedded GIF — 45m
- [ ] 5.12 LinkedIn post — 30m

---

## Recent decisions log
- 2026-05-07 (Day 0, pre-Sat-W1): repo restructured flat `backend/*.py` rather
  than nested `domain/adapters/api`. Layering will emerge as 1.3/1.7 rewrite
  modules. Avoids dead-weight churn in 1.1.
- 2026-05-07: 1.2 expanded by ~15m to absorb architect review (idempotency
  table, signed_payload, revoked_at, razorpay IDs on receipts, flat replay
  columns). All confirmed by user before write.
- 2026-05-07: ADR-009 (JSONB embeddings) and ADR-010 (DID namespace) added.
- 2026-05-07: Approval-status columns on negotiation_sessions deferred to
  backlog Tier 1.5 — MCP-first flow has no separate approval step.
