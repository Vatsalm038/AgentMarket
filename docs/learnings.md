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
- 2.3: installing `fastmcp` upgraded `starlette` to 1.0, which broke `fastapi==0.115` at app construction (`Router.__init__()` got an unexpected `on_startup` kwarg). Fixed by bumping fastapi to 0.136. Lifespan context manager was already wired since Day 1 so no app-code change was needed — just version bumps. Lesson: pin the whole transitive graph (`fastapi`, `starlette`, `pydantic`, `httpx`, `cryptography`, `fastmcp`, `mcp`) to exact versions, especially crypto since Ed25519 is rule #2.
- 2.1 + bonus: `AsyncOpenAI()` was being instantiated at module import in THREE files (matcher.py, auction.py, negotiation.py). This breaks boot whenever `OPENAI_API_KEY` is missing — migrations, lint, CI, even `python -c "from backend.main import app"`. Fixed all three with a lazy `_get_openai_client()` getter. Pattern to use going forward; flag in code review whenever a new module imports the OpenAI client at top level.
- 2.6 / 2.7: the two backlog Tier 1.2 items (`/agents/{id}/pubkey` and richer `/commerce/session/{id}`) became unavoidable the moment the MCP tools were written — verify_receipt couldn't independently fetch a pubkey, and get_audit_trail had nowhere to read the signed receipt from. Folding them into the tool tickets was cheaper than holding them at backlog. Lesson: backlog items that block multiple downstream tickets should be promoted into one of those tickets, not deferred separately.
- 2.5: MCP tools can't accept a long-lived buyer keypair from Claude.ai (no per-user state). MVP pattern: register ONE demo buyer agent at MCP server boot, hold the keypair in module-level state, never persist or return it. Restart MCP server = fresh agent. Documented for the demo video. Production multi-tenant is post-hire.
- 2.9: replay capture was instrumented inside `auction.py`'s LLM call sites (merchant_quote + buyer_eval) and accumulated into `negotiation_sessions.replay_data` JSONB. The replay tool re-calls OpenAI with the same model/temp=0/seed and compares. OpenAI's seed is best-effort; replay tool reports match=False honestly when determinism breaks — that's a feature, not a bug.
- 2.10/review: the code-reviewer agent caught a quiet rule-7 violation — the initial 2.8 design persisted the platform Ed25519 private key in a `platform_keys` table with a hand-waved docstring "rule scoped to agent keys only". CLAUDE.md rules are non-negotiable; a unilateral scope-narrowing inside a model docstring is not a valid carve-out. Lesson: when a fix to one rule feels like it needs a re-interpretation of another rule, write an ADR first or pick a different design. The fix was easy (env-or-ephemeral module cache) — the bad-instinct was the warning sign.
- 2.10/review: MCP `negotiate` initially used `uuid.uuid4()` for the Idempotency-Key, which structurally defeats rule 3 — a Claude retry would re-run the auction and re-spend the buyer's policy. Idempotency keys should be **deterministic from the inputs** for any client that retries idempotent operations (which Claude does on transport hiccups). Fix: `sha256(json.dumps(canonical_inputs, sort_keys=True))`. Pattern to flag whenever a UUID appears in an idempotency context.
- 2.10/review: auction settle path was passing `validate_spend(credential, winner_price)` without `daily_spent`, so the daily cap was unenforced for auctions while it WAS enforced for negotiate. Easy silent class of bug — same helper, different arity at different call sites. Worth a quick `grep -n validate_spend` audit whenever a new caller is added.

## Day 3
- _(your first surprise here)_

## Day 4
- _(your first surprise here)_

## Day 5
- _(your first surprise here)_
