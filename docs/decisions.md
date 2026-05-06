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

_(append new ADRs below as decisions are made)_
