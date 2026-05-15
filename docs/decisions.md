# Architecture Decision Records

Format: ADR-NNN | Date | Status | Decision | Context | Consequences

---

## ADR-001 | Day 1 | Accepted
**Decision:** Ed25519 for all signing. RSA banned.
**Context:** Original prototype used RSA-2048 PKCS1v15+SHA256. Ed25519 is the modern
standard (Cloudflare, Stripe, OpenSSH, WireGuard).
**Consequences:** 64-byte signatures vs 256, faster, no padding pitfalls. Existing
prototype data is dev-only, regenerate.

## ADR-002 | Day 1 | Accepted
**Decision:** Standardize on OpenAI gpt-4o-mini. Embeddings via text-embedding-3-small.
**Context:** Codebase had inconsistency (README said Anthropic, code used OpenAI).
**Consequences:** Single OPENAI_API_KEY. LLM_PROVIDER env var for future swap.

## ADR-003 | Day 1 | Accepted
**Decision:** Local Indian commerce vertical (AgentMarket). Two-sided marketplace.
**Context:** Considered B2B procurement, salary coach, refund agent, tenant rights.
Vatsal's original idea fits his context (Mumbai), his existing architecture, and
his "actually help people" instinct.
**Consequences:** MVP seeds merchant data manually (no real merchants in 5 days).
Real merchant acquisition is post-hire. Cold-start problem accepted as known risk.

## ADR-004 | Day 1 | Accepted
**Decision:** No custom user-written agent prompts. 6 presets only.
**Context:** Custom prompts = security risk (injection, breaking math clamps) +
quality risk (bad prompts → bad UX → blame on platform).
**Consequences:** Skill marketplace deferred. backlog.md item: sandboxed custom skills.

## ADR-005 | Day 1 | Accepted
**Decision:** Razorpay test mode only.
**Context:** RBI's stance on AI-authorized variable UPI debits unsettled (2026).
Live mode without legal review = regulatory + reputational risk.
**Consequences:** Demo uses test cards / success@razorpay only. Banner: "Test mode."

## ADR-006 | Day 1 | Accepted
**Decision:** MCP-first as primary distribution. No buyer dashboard, no merchant dashboard for MVP.
**Context:** MCP is rare in 2026 portfolios. Building dashboards eats days that
should go to depth. MCP-first matches the "AI agents as primary interface" thesis.
**Consequences:** Buyers interact via Claude/ChatGPT. Web UI exists only to show
signed policy + trail + receipt. Merchants admin via direct SQL for MVP.

## ADR-007 | Day 1 | Accepted
**Decision:** "Verifiable Replay" as the technical differentiator. Not Bayesian, not reputation.
**Context:** Three options considered. Replay is simplest (~50 lines), demos best
(reproducibility narrative), and addresses real concerns (AI auditability).
**Consequences:** Every LLM call stores prompt + model + temperature=0 + seed.
replay_negotiation MCP tool re-runs and compares outcomes.

## ADR-008 | Day 1 | Accepted
**Decision:** Aesthetic = Anthropic console / Stripe dashboard / Linear / bank.
**Context:** Vatsal explicitly requested grayscale, audit-trail aesthetic. Avoids
"AI startup with neon purple" trap.
**Consequences:** shadcn zinc theme, no gradients, no blue primary, tables over cards.
See docs/design-system.md for full rules.

---

## ADR-009 | Day 1 | Accepted
**Decision:** Store product embeddings as `JSONB` float arrays for MVP. Defer
`pgvector` until post-hire scale demands it.
**Context:** Local Postgres (12.22) does not have `pgvector` available;
installing requires `apt install postgresql-12-pgvector` + server restart.
Embedding count at MVP demo is ~800 (20 merchants × ~40 products), so an
in-Python cosine similarity scan is O(800) per matcher call — well under 10ms.
**Consequences:** Matcher (ticket 2.1) loads all active product embeddings into
memory and computes similarity in numpy. Will not scale beyond ~10k products;
swap to `pgvector` is a one-migration job (alter column type to `vector(1536)`,
add ivfflat index). Captured `embedding_model` and `embedding_generated_at`
columns now so a future model swap can identify stale rows.

## ADR-010 | Day 1 | Accepted
**Decision:** DID namespace prefixes — buyers use `did:agent:*`, merchants
use `did:merchant:*`. Enforced by app-side ID generators, not a DB CHECK.
**Context:** `agents.id` and `merchant_agents.id` are both string PKs. A
careless join could silently match a buyer DID against a merchant DID and
return wrong rows. Architect flagged this during 1.2 review.
**Consequences:** `generate_agent_id()` and `generate_merchant_agent_id()`
will live in domain code with the prefix baked in. Migration enforces FK
target tables, which prevents the bug at the schema level; the prefix is
defence-in-depth.

---

## ADR-011 | 2026-05-11 | Accepted
**Decision:** Auction shortlists competitors via a simple SQL query
(category + is_active + listed_price <= policy_max, ordered by floor_price ASC,
LIMIT 3 *including* the anchor) keyed off an anchor `product_id`. Matcher
(ticket 2.1) remains responsible for selecting the anchor; auction does not
call the matcher.
**Context:** 1.7 must move `auction.py` off hard-coded merchant names without
duplicating matcher work that 2.1 will write. Auction's job is competitive
quote collection, not buyer-intent resolution. Current signature
`run_auction(item, listed_price, ...)` assumes the caller has already
resolved a product but still passes free-text + price, which leaves the
floor-price clamp guessing (`listed_price * 0.70`) instead of using the real
seeded `floor_price`.
**Consequences:** `run_auction` signature changes to
`(session, anchor_product_id, credential, buyer_priorities, num_merchants=3)`
and becomes `async`. The floor-price clamp now uses each row's seeded
`floor_price` rather than a fixed 70% of listed. Each merchant_agent's
bound `skill_id` (from 1.8) is used — never randomised, so replay stays
deterministic. DB session is dependency-injected from the caller so the
auction shares the caller's transaction (audit_log + negotiation_sessions
write atomically). When 2.1 ships, the inline `_shortlist_competitors`
helper is swapped for `matcher.shortlist_competitors()` in one line.
**Follow-up:** add composite index on `products(category, is_active)`
before the MVP demo; confirm `merchant_agents.merchant_id` is 1:1 (add a
unique constraint if so) to prevent shortlist duplication on join.

---

_(append new ADRs below as decisions are made)_

---

## ADR-012 | 2026-05-15 | Accepted
**Decision:** Rebrand to SignedDeals. Drop MCP server. Add `users` table as
top-level auth entity with dual buyer/merchant roles. Multi-merchant auction
(3-4 competing merchants) and full Ed25519/DID system remain unchanged.
Razorpay stays in test mode throughout MVP — no live money. Three React surfaces:
buyer dashboard, merchant dashboard, marketing website (shared Vite app,
configurable post-MVP). Google OAuth, product/delivery-proof images (Cloudflare R2),
custom skills, B2B Excel upload, blog CMS deferred to post-MVP.

**Context:** C2C + SMB expansion. MCP dropped because web dashboard is the
primary interface and a solo schedule cannot maintain two distribution paths.
Multi-merchant auction stays because 3-4 competing agents is the core value
demonstration — the negotiation trail must show real competition. Ed25519 + DID
system is unchanged (signing, policy delegation, verifiable receipts all intact).
Live Razorpay deferred pending legal/RBI review of AI-authorized UPI debits.

**Consequences:**
1. `users` table (UUID PK, email, bcrypt hash, google_id nullable, is_buyer bool,
   is_merchant bool). Existing `agents.owner_id` string stays (signed payload
   compat); `agents.owner_user_id UUID FK → users` added alongside it.
   `buyers` table absorbed into `users`.
2. JWT auth (python-jose, HS256). All `/commerce/*` routes gated behind JWT in
   Phase 3 (after frontend is ready). New route groups: `/auth`, `/merchant`,
   `/buyer`, `/skills`, `/payments`, `/admin`.
3. New tables: `deliveries` (delivery tracking), `delivery_reminders`,
   `subscribers`. Modified: `products` (image_url nullable, delivery fields),
   `negotiation_sessions` (pay_later status, pay_later_due_date), `signed_receipts`
   (platform_fee_paise, platform_fee_pct), `agent_skills` (owner_id, visibility),
   `merchants` (owner_id FK → users).
4. Platform fee: `PLATFORM_FEE_PCT` env var (default 2.5%). Python arithmetic at
   settlement, stored in `signed_receipts.platform_fee_paise`. No Razorpay Route —
   manual reconciliation for MVP.
5. Pay later: status values `pay_later | payment_initiated` added to
   `negotiation_sessions`. "Pay Now" creates Razorpay order on demand.
6. Email via Resend API. 2 MVP templates: deal_closed, delivery_reminder.
   Render cron job hits `POST /admin/send-reminders`.
7. Frontend: three route groups sharing one Vite app — `/` (marketing),
   `/buyer/*` (buyer dashboard), `/merchant/*` (merchant dashboard). Marketing
   pages configurable/extractable post-MVP. Zinc dark theme for dashboards;
   zinc-900 hero + white body sections for marketing.
8. Image storage deferred. `image_url` columns added nullable; upload via
   Cloudflare R2 presigned URLs ships post-MVP.
9. mcp_server/ directory removed. render.yaml updated to single backend service.
