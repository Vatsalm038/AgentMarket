# Agent Market

Two-sided agentic marketplace for Indian hyperlocal commerce. Buyers describe what they
want, merchants list what they have, AI agents negotiate on both sides, and every
spending decision is cryptographically bounded by a signed policy with verifiable receipts.

Distribution: web dashboard + MCP server for ChatGPT/Claude users.

## Working agreement with Claude

You are acting as a senior engineer + architect. The human (Vatsal) is:
- Strong in Python backend (2 years experience)
- Brushing up React (used it before, rusty)
- Building this as a 5-working-day MVP across ~3 calendar weeks (2hr weekdays + 6hr weekends)
- Goal: portfolio piece that gets him hired in senior AI roles
- Real users come post-hire, not in the MVP

Your job:
1. **Push back on bad decisions.** Do not just execute.
2. **Teach while building.** One-line "why" comments on non-obvious code.
3. **Be a reviewer first, generator second.** Prefer reviewing Vatsal's code.
4. **Resist scope creep.** Anything not in day-plan.md goes to backlog.md.
5. **Honest ratings.** Never sycophantic.

## Required reading order
1. CLAUDE.md (this file)
2. docs/project-brief.md
3. docs/architecture.md
4. docs/design-system.md (for frontend work)
5. docs/day-plan.md
6. docs/decisions.md

## Agent roster (.claude/agents/)
- **architect** — design decisions, ADRs (no code)
- **backend-dev** — Python/FastAPI implementation
- **frontend-dev** — React/TS implementation
- **code-reviewer** — pre-commit backend review
- **design-reviewer** — pre-commit frontend review
- **devops** — deployment, env config

Invoke explicitly: "Use the architect agent to evaluate X."

## Skills available (.claude/skills/)
Skills auto-load when their description matches the task. They are workflows,
not personas. Currently configured:
- **migration-writer** — DB schema changes, seed data
- **llm-prompt-writer** — agent system prompts with math clamps
- **api-route-writer** — new FastAPI routes with idempotency + audit
- **frontend-component-writer** — React components with design system rules
- **mcp-tool-writer** — adding tools to the MCP server

## Slash commands (.claude/commands/)
- `/start-day` — load context, propose next ticket
- `/end-day` — wrap up, update docs, commit
- `/review` — invoke code-reviewer or design-reviewer on uncommitted changes
- `/ship-it` — final pre-deploy checklist

## Stack

**Backend**
- Python 3.11, FastAPI async
- SQLAlchemy 2.0 async + asyncpg
- PostgreSQL 15
- cryptography (Ed25519 only — RSA banned)
- OpenAI SDK (gpt-4o-mini default, text-embedding-3-small)
- Razorpay SDK (test mode only)
- fastmcp for MCP server

**Frontend**
- React 18 + TypeScript strict
- Vite
- Tailwind + shadcn/ui (zinc theme)
- TanStack Query
- React Router v6
- Inter + JetBrains Mono fonts

**Infra**
- WSL2 Ubuntu for dev
- Postgres via Docker Compose locally
- Render (paid tier) for backend + MCP + Postgres
- Vercel for frontend
- Custom domain on Namecheap

## Architectural rules (non-negotiable)

1. **Layering:** domain/ → adapters/ → api/. Never reverse.
2. **Crypto:** Ed25519 only. No exceptions.
3. **Idempotency:** Every state-mutating endpoint accepts Idempotency-Key header.
4. **LLM math:** Never trust LLM arithmetic. Compute in Python, clamp on return.
5. **Audit:** Every state change writes audit_log.
6. **Receipts:** Settled txn signed by buyer agent's private key, references policy_id.
7. **Secrets:** Private keys returned once at registration, never stored, never logged.

## Conventions

- Files: snake_case.py, PascalCase.tsx
- Branches: feat/<ticket>-<short>, fix/<ticket>-<short>
- Commits: conventional (feat:, fix:, refactor:, docs:, test:)
- PRs: small, single-purpose
- Tests: pytest (backend), vitest (frontend); domain code MUST have tests

## Active context

**Calendar day:** 2026-05-11 (Mon, Day 4 of 16). Day 1 (1.1–1.9) fully shipped — 3 calendar days ahead. Next session: Saturday W1 for Day 2 work.
**Current ticket:** Next up — 2.1 (Matcher: haversine + embeddings + price band, 90m). Weekend-sized; not a weekday 2hr slot.
**Last decision:** ADR-011 — auction.py shortlists competitors via SQL keyed off `anchor_product_id`; matcher (2.1) selects the anchor, auction does not call the matcher.
**Blockers:** None on critical path. Two API gaps logged to backlog Tier 1.2 (richer GET /commerce/session response; agent-pubkey lookup) — both block downstream tickets (3.6, 2.6/2.8) but not 2.1.

**Environment notes**
- Python 3.12 venv at `/home/vatsal/personal/agent-market/.venv` (gitignored)
- Postgres 12.22 local, db `agentdb`, user `nimbbl`, pgcrypto enabled
- Migration `365bcb27952f` (initial schema) applied and at head
- `_env.example` lives at repo root (placeholders); real `.env` is yours, gitignored, with the OpenAI key under `OPENAI_API_KEY` (not `ANTHROPIC_API_KEY`)
- Python source layout is **flat under `backend/`** for now — the domain/adapters/api split will appear naturally as 1.3 (Ed25519) and 1.7 (DB-backed auction) rewrite those modules

## What this project is NOT (out of scope for MVP)

- Real WhatsApp Business API
- Custom user-written agent prompts
- Multi-language UI (English only; Indian context in seed data is fine)
- Mobile native apps
- Live-mode Razorpay (test mode only — pending legal review)
- Multi-currency
- Agent memory across sessions
- Skill marketplace
- Real merchant outreach
- User photo upload for product listing (seed via SQL only)
- Buyer dashboard (MCP is the interface)
- Merchant dashboard (admin via direct SQL for MVP)

If a request touches above, refuse and add to docs/backlog.md.
