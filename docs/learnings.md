# Learnings

One-liners. Capture surprises while building. No structure required.

## Day 1
- Local Postgres is **12.22**, not 15. `gen_random_uuid()` is built-in only from PG 13 — needed `CREATE EXTENSION pgcrypto` in the migration. Render's managed PG will be ≥15, but the extension call is a safe no-op there.
- pgvector not available on the local install. Falling back to JSONB embeddings is fine at MVP scale (~800 products) — ADR-009 captures the deferral.
- The `_env.example` previously had a real-looking key in working tree; git history was clean (committed copy had placeholder). Lesson: even untracked dotfiles need a sanity-check before any `git add -A`.
- The `ANTHROPIC_API_KEY` in `.env` was actually an OpenAI key (`sk-proj-` prefix). Variable-name drift would have silently failed. ADR-002 says OpenAI canonical — renamed.
- Architect agent caught a non-obvious must-fix: store `signed_payload` bytes on policies + receipts, not just the signature. Reconstructing canonical bytes from columns later = bug factory.

## Day 2
- _(your first surprise here)_

## Day 3
- _(your first surprise here)_

## Day 4
- _(your first surprise here)_

## Day 5
- _(your first surprise here)_
