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

- [x] 1.1 Restructure repo (backend/, mcp-server/, frontend/, docs/, .claude/) — 30m
- [x] 1.2 Schema migration: drop old, add merchants/products/merchant_agents/agent_skills/signed_receipts. Fix FK drift. — 60m (~75m actual; +idempotency_keys table, signed_payload columns, replay flat columns)
- [x] 1.3 RSA → Ed25519 in identity.py + settlement.py — 45m (tests green; merchant DID generator added per ADR-010)
- [x] 1.4 Fix policy_id linkage in receipts — 20m (credential carries policy_id; receipt signature commits to the real spending_policies row)
- [x] 1.5 Add idempotency keys to settlement — 45m (expanded: full models.py rewrite to mirror migration, signed_receipts persistence, create_transaction returns (payload, signed_bytes), Idempotency-Key header on /commerce/negotiate + /commerce/auction)
- [x] 1.6 Seed 20 Mumbai merchants × ~40 products with realistic INR floor prices — 60m (20 merchants × 30-50 products = 669 rows; idempotent via ON CONFLICT DO NOTHING; price helper unit-tested)
- [x] 1.7 Refactor auction.py to read merchants/products from DB — 60m (ADR-011: async run_auction(db, anchor_product_id, ...); shortlist by category+active ordered by floor_price; real floor_price clamp; bound skill_id per merchant_agent; temperature=0 + per-(auction,merchant) seed for replay; AuctionRequest swapped to anchor_product_id; placeholder fixtures dropped from auction path; folded merchant_agents seed into scripts/seed.py)
- [x] 1.8 Seed 6 agent skills (personas) — 30m (6 rows in agent_skills; deterministic IDs; prompts parameterized by {role} with explicit price-band clamps + JSON contract; idempotent)
- [x] 1.9 End-to-end script scripts/demo_endtoend.py — 90m (HTTP-only demo + smoke test against local uvicorn; deterministic anchor prod_merch_003_09 Canvas Wallet/Andheri; verifies receipt Ed25519 sig client-side using public key captured at /agents/register; idempotency replay byte-identical; replay fields read from audit_log)
## Day 2 — Matcher + MCP

- [ ] 2.1 Matcher: haversine + embeddings + price band — 90m
- [ ] 2.2 Pre-compute product embeddings — 20m
- [ ] 2.3 MCP server scaffold (fastmcp, port 8001) — 45m
- [ ] 2.4 MCP tool: search_local_merchants — 45m
- [ ] 2.5 MCP tool: negotiate — 90m
- [ ] 2.6 MCP tool: verify_receipt — 45m
- [ ] 2.7 MCP tool: get_audit_trail — 30m
- [ ] 2.8 /well-known/platform-pubkey endpoint — 15m
- [ ] 2.9 Verifiable replay: store prompts + seed in replay_data, add replay_negotiation tool — 60m
- [ ] 2.10 Test full flow in Claude.ai with local MCP — 30m

## Day 3 — Frontend (Anthropic/bank aesthetic)

- [ ] 3.1 Vite + React + TS + Tailwind + shadcn (zinc theme) — 45m
- [ ] 3.2 TanStack Query, axios client, types — 30m
- [ ] 3.3 Landing page / — 60m
- [ ] 3.4 /session/:id (auth + trail + receipt sections) — 210m
- [ ] 3.5 /sessions table list — 60m
- [ ] 3.6 /replay/:id side-by-side — 90m
- [ ] 3.7 /install-mcp copy-paste page — 45m
- [ ] 3.8 Empty states, skeletons, error boundaries — 45m

## Day 4 — Razorpay + WebSocket + audit polish

- [ ] 4.1 Razorpay test mode integration end-to-end — 90m
- [ ] 4.2 Webhook signature verification — 30m
- [ ] 4.3 WebSocket /ws/session/:id streaming — 60m
- [ ] 4.4 Frontend live updates via WebSocket — 45m
- [ ] 4.5 Audit log polish + show-full toggle — 60m
- [ ] 4.6 "Download signed receipt" button — 20m
- [ ] 4.7 /verify standalone page — 45m

## Day 5 — Deploy + video + launch

- [ ] 5.1 Postgres on Render paid tier — 20m
- [ ] 5.2 Backend on Render — 30m
- [ ] 5.3 MCP server on Render — 20m
- [ ] 5.4 Frontend on Vercel — 20m
- [ ] 5.5 Custom domain + DNS — 30m
- [ ] 5.6 Run migrations + seed in production — 30m
- [ ] 5.7 Smoke test all 4 MCP tools against production — 30m
- [ ] 5.8 Record 3-min demo video (script in docs/demo-script.md) — 180m
- [ ] 5.9 Edit video — 90m
- [ ] 5.10 README rewrite with embedded GIF — 45m
- [ ] 5.11 LinkedIn post — 30m
- [ ] 5.12 Resume bullet — 15m

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
