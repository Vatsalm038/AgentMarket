# Agent Market

AgentMarket is a two-sided agentic marketplace for Indian hyperlocal commerce. Buyers describe what they want in natural language; AI agents then run a multi-merchant auction, negotiate prices, and produce a verifiable settlement. Every spending decision is cryptographically bounded by an Ed25519-signed delegation policy — no money can move beyond what the buyer pre-authorised. Every transaction produces a signed receipt with verifiable replay: you can re-run the exact LLM prompts and confirm the auction output is reproducible. The primary interface for buyers is the MCP server, which connects AgentMarket as a tool inside Claude.ai or ChatGPT.

**Status:** MVP in progress (5 working days, ~3 calendar weeks).
**Important:** Razorpay is in test mode only — no real money moves.

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
# 1. Clone and set up env
cp _env.example .env
# Edit .env — fill in OPENAI_API_KEY, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET,
# and generate PLATFORM_PRIVATE_KEY_B64 using the command in _env.example.

# 2. Start Postgres
docker compose up -d

# 3. Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
python scripts/seed.py
python scripts/embed_products.py     # ~2 min, ~$0.001 in embedding costs
uvicorn main:app --reload --port 8000

# 4. MCP server (separate terminal, from mcp_server/)
cd mcp_server
pip install -r requirements.txt
python server.py                     # serves on port 8001

# 5. Frontend
cd frontend
npm install
npm run dev                          # serves on port 5173, proxies /api → :8000
```

To connect the MCP server to Claude.ai, visit `/install-mcp` once the backend is running.

See [docs/architecture.md](docs/architecture.md) for a full system diagram and module guide.

## Demo

(Coming Day 5 — a 3-minute video showing the full flow from inside Claude.ai)

## License

MIT (or whatever Vatsal chooses post-MVP)
