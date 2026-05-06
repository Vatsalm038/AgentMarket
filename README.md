# Agent Market

> Two-sided agentic marketplace for Indian hyperlocal commerce.
> AI agents negotiate on behalf of buyers and merchants. Every spending decision
> is cryptographically bounded; every transaction is verifiable.

**Status:** MVP in progress (5 working days, ~3 calendar weeks).

## Quick links
- [Project brief](docs/project-brief.md) — what we're building and why
- [Architecture](docs/architecture.md) — how the system fits together
- [Design system](docs/design-system.md) — frontend aesthetic rules
- [Day plan](docs/day-plan.md) — current ticket queue
- [Decisions](docs/decisions.md) — ADRs, the why-this-way log
- [Backlog](docs/backlog.md) — explicitly out of MVP scope

## Stack

**Backend:** Python 3.11, FastAPI, async SQLAlchemy, PostgreSQL, Ed25519,
OpenAI gpt-4o-mini + embeddings, Razorpay (test mode).

**Frontend:** React 18, TypeScript, Vite, Tailwind, shadcn/ui (zinc theme),
TanStack Query.

**Distribution:** Web dashboard + MCP server for ChatGPT/Claude users.

## Working with Claude Code

This repo is set up for Claude Code from day one. The `.claude/` directory has:
- `agents/` — 6 specialist subagents (architect, backend-dev, frontend-dev,
  code-reviewer, design-reviewer, devops)
- `skills/` — 5 reusable workflows (migrations, prompts, API routes,
  frontend components, MCP tools)
- `commands/` — slash commands (`/start-day`, `/end-day`, `/review`, `/ship-it`)

Start every session with `/start-day` to load context and pick the next ticket.

## Local dev

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d postgres
alembic upgrade head  # or run migrations/ SQL files manually
uvicorn app.api.main:app --reload --port 8000

# MCP server
cd mcp-server
pip install -r requirements.txt
python -m mcp_server  # serves on port 8001

# Frontend
cd frontend
npm install
npm run dev  # serves on port 5173
```

## Demo

(Coming Day 5 — a 3-minute video showing the full flow from inside Claude.ai)

## License

MIT (or whatever Vatsal chooses post-MVP)
