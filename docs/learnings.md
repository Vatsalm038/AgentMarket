# Learnings

One-liners. Capture surprises while building. No structure required.

## Day 1
- Local Postgres is **12.22**, not 15. `gen_random_uuid()` is built-in only from PG 13 — needed `CREATE EXTENSION pgcrypto` in the migration. Render's managed PG will be ≥15, but the extension call is a safe no-op there.
- pgvector not available on the local install. Falling back to JSONB embeddings is fine at MVP scale (~800 products) — ADR-009 captures the deferral.
- The `_env.example` previously had a real-looking key in working tree; git history was clean (committed copy had placeholder). Lesson: even untracked dotfiles need a sanity-check before any `git add -A`.
- The `ANTHROPIC_API_KEY` in `.env` was actually an OpenAI key (`sk-proj-` prefix). Variable-name drift would have silently failed. ADR-002 says OpenAI canonical — renamed.
- Architect agent caught a non-obvious must-fix: store `signed_payload` bytes on policies + receipts, not just the signature. Reconstructing canonical bytes from columns later = bug factory.
- 1.7: the auction's shortlist query (`products.category = ? AND is_active AND listed_price <= ?`, order by floor_price) has no covering index — single composite index on `(category, is_active)` would make it cheap. Added to ADR-011 follow-up; deferred to a tiny migration after 2.1's matcher lands so we add both indexes at once.
- 1.7: 1.6 seeded merchants + products but NOT `merchant_agents`, and `negotiation_sessions.merchant_agent_id` is NOT NULL — so the new DB-backed auction would have failed on the first settled session. Folded an idempotent `seed_merchant_agents` step into `scripts/seed.py` (one agent per merchant, skill round-robined, deterministic Ed25519 keys for replay). Lesson: any "seed real fixtures" ticket needs to walk the full FK closure of the tables touched downstream, not just the headline tables.
- 1.7: `merchant_agents.merchant_id` has no UNIQUE constraint, which means a future second merchant_agent per merchant would silently duplicate products in the auction shortlist (cross join). Mitigated in code with a `seen_merchant_agents` dedupe set; recommended a DB-level UNIQUE in the next migration (ADR-011 follow-up).
- 1.9: `/commerce/auction` returned `auction_id` while `/commerce/negotiate` returned `session_id` — same row underneath. Asymmetry caught only when the demo script hit both. Renamed to `session_id` everywhere; local variable kept. Lesson: cross-endpoint shape consistency is invisible until something exercises both.
- 1.9: `GET /commerce/session/{id}` does NOT surface the flat `winner_skill_id` / `llm_seed` / `signed_receipts` row — replay fields are only reachable inside `audit_log[*].payload`. The /replay/:id page (3.6) and MCP `verify_receipt` (2.6) will need a richer response. Parked in backlog Tier 1.2.
- 1.9: no agent-pubkey lookup endpoint exists. The demo works around this by capturing the public key returned at `/agents/register`, but any external verifier (MCP 2.6, /verify standalone page 4.7) needs `GET /agents/{id}/pubkey` or `/well-known/platform-pubkey` (2.8) before it can verify a receipt it didn't witness being issued.

## Day 2
- _(your first surprise here)_

## Day 3
- _(your first surprise here)_

## Day 4
- _(your first surprise here)_

## Day 5
- _(your first surprise here)_
