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

_(append new ADRs below as decisions are made)_
