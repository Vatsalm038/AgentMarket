# Fresh-laptop bootstrap

Step-by-step to bring a clean machine up to "all 45 tests green + MCP demo
working" state. Tested target: Ubuntu 22.04+ (WSL2 or native) on Python 3.12.

## 0. System prereqs

```bash
sudo apt update
sudo apt install -y \
  build-essential git curl \
  python3.12 python3.12-venv python3.12-dev \
  postgresql-14 postgresql-contrib \
  libpq-dev
# (Postgres 14+ works. Original dev used 12; 14 ships built-in gen_random_uuid.)
```

Node is **not** needed yet — frontend (Day 3) hasn't been built.

Optional but useful:

```bash
sudo apt install -y cloudflared   # or: snap install ngrok
```

## 1. Clone

```bash
cd ~/personal
git clone git@github.com:<your-handle>/agent-market.git
cd agent-market
```

## 2. Python venv + deps

```bash
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r backend/requirements.txt
```

Pinned set (see `backend/requirements.txt`): fastapi 0.136, starlette 1.0,
sqlalchemy 2.0.35 (+ asyncio), asyncpg 0.29, cryptography 48, openai 2.35,
fastmcp 3.2.4, razorpay 1.4.1, alembic 1.13. Don't drift these — see
`docs/learnings.md` Day 2 entry 2.3 for the FastAPI/starlette breakage story.

## 3. Postgres

Start the service and create the dev db/user the env file expects:

```bash
sudo service postgresql start

sudo -u postgres psql <<SQL
CREATE USER agentuser WITH PASSWORD 'agentpass';
CREATE DATABASE agentdb OWNER agentuser;
GRANT ALL PRIVILEGES ON DATABASE agentdb TO agentuser;
\c agentdb
CREATE EXTENSION IF NOT EXISTS pgcrypto;
SQL
```

(If you keep the original dev DSN `nimbbl/agentdb`, substitute that user
instead.)

Confirm:

```bash
PGPASSWORD=agentpass psql -h localhost -U agentuser -d agentdb -c '\dx'
```

## 4. Environment

```bash
cp _env.example .env
$EDITOR .env
```

Required:

- `DATABASE_URL=postgresql+asyncpg://agentuser:agentpass@localhost/agentdb`
- `OPENAI_API_KEY=sk-proj-...` (canonical per ADR-002 — **not** ANTHROPIC_API_KEY)

Optional but recommended:

- `PLATFORM_PRIVATE_KEY_B64=<32-byte base64>` — pins the platform Ed25519
  key across restarts. If unset, the backend generates an ephemeral key at
  startup and logs the base64 to pin. Never commit this value.
- `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` — test-mode only (ADR-005).
  Razorpay isn't exercised until Day 4 (ticket 4.1).

## 5. Database schema + seed

```bash
cd backend
../.venv/bin/alembic upgrade head           # apply all migrations
../.venv/bin/python -m scripts.seed         # 20 merchants + ~669 products + 6 skills + 20 merchant_agents
../.venv/bin/python -m scripts.embed_products  # backfill text-embedding-3-small (idempotent; ~$0.0005)
cd ..
```

`embed_products` makes a live OpenAI call — make sure `OPENAI_API_KEY` is
exported (`set -a; source .env; set +a`) or pass it inline.

## 6. Tests

```bash
.venv/bin/python -m pytest backend/tests.py -q
```

Expected: **45 passed**. Some `datetime.utcnow()` deprecation warnings are
known and tracked in backlog.

## 7. Smoke-test the API + MCP

Two terminals — see [`mcp-setup.md`](./mcp-setup.md) for the exact commands
and the Claude.ai connector flow. Minimum:

```bash
# T1
cd backend && ../.venv/bin/uvicorn main:app --port 8000 --host 127.0.0.1
# T2
.venv/bin/python -m mcp_server.server
# T3
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/.well-known/platform-pubkey
```

If `/.well-known/platform-pubkey` returns `source: ephemeral`, pin the
suggested `PLATFORM_PRIVATE_KEY_B64` value from the backend log into your
`.env`.

End-to-end demo script (HTTP only, no MCP):

```bash
cd backend && ../.venv/bin/python -m scripts.demo_endtoend
```

## 8. Resume state

Pick up from:

- `docs/day-plan.md` — current ticket
- `docs/decisions.md` — ADR history
- `docs/learnings.md` — non-obvious gotchas already paid for
- `docs/backlog.md` — what's been deferred

Day 2 was completed 2026-05-12 (all of 2.4–2.10). Day 3 (frontend) is the
next plan-day. Frontend dir is still empty — `frontend/` will be initialised
with Vite at ticket 3.1.

## Pitfalls already discovered

- **Flat imports**: backend modules do `from auction import ...`, not
  `from backend.auction import ...`. Always `cd backend/` before `uvicorn`.
  See `docs/learnings.md` Day 1.
- **OpenAI client lazy-init**: never instantiate `AsyncOpenAI()` at module
  import. Use a `_get_openai_client()` getter pattern (see `auction.py`).
  Otherwise migrations / `python -c "import main"` break when the key is
  missing. Day 2 entry in `learnings.md`.
- **Ed25519 only** (ADR-001 + CLAUDE.md rule 2). No RSA anywhere. Includes
  the platform key.
- **Private keys never persisted** (CLAUDE.md rule 7). Backend rejects this
  rule for ANY key including the platform's. Use env or accept ephemeral
  dev keys.
- **Idempotency-Key on state mutations** (rule 3). Auction + negotiate
  endpoints require the header; MCP `negotiate` tool derives its key
  deterministically from inputs so client retries hit cache.
- **Local Postgres 12 lacked `gen_random_uuid`** — fixed via `pgcrypto`
  extension in the initial migration. 14+ has it built in but the extension
  call is a safe no-op.
