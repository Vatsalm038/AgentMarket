---
name: migration-writer
description: Use when adding tables, columns, indexes, constraints, or seed data to PostgreSQL. Writes idempotent migration files.
---

# Writing Migrations for AgentMarket

## When to use
- Any schema change (CREATE TABLE, ALTER TABLE, CREATE INDEX, etc.)
- Adding seed data (agent_skills, mumbai merchants, products, etc.)
- Fixing FK drift or missing constraints

## File pattern
- Path: `backend/migrations/NNN_short_name.sql`
- Sequential 3-digit numbering, never reuse numbers
- Existing migrations don't get edited — write a new one to amend

## Idempotency requirements
- `CREATE TABLE IF NOT EXISTS`
- `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
- `CREATE INDEX IF NOT EXISTS`
- For seed data, use `ON CONFLICT (id) DO NOTHING` or `ON CONFLICT DO UPDATE`
- A migration must be safely re-runnable on a DB where it's already applied

## What every migration must include
- FK constraints (the original Sql.txt schema is missing several — see ADR-001 in decisions.md)
- Indexes on FKs
- Indexes on columns used in WHERE clauses
- Comment block at top explaining why this migration exists

## Template
```sql
-- Migration NNN: <short name>
-- Why: <one-paragraph reason>
-- Reversible: <yes/no — if yes, include rollback notes; if no, explain>
-- Author: <date>

BEGIN;

-- Create table
CREATE TABLE IF NOT EXISTS table_name (
    id varchar PRIMARY KEY,
    -- ... columns ...
    created_at timestamp DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_table_name_fk ON table_name(fk_column);

-- FK constraints
ALTER TABLE table_name
  ADD CONSTRAINT fk_table_name_other
  FOREIGN KEY (other_id) REFERENCES other_table(id)
  ON DELETE RESTRICT;

COMMIT;
```

## Rules
- No `DROP TABLE` without explicit user approval in chat
- No `DELETE FROM` for production-shape tables without explicit approval
- Always test migration on dev DB (`docker compose exec postgres psql -U agentuser -d agentdb -f migrations/NNN_x.sql`) before committing
- Seed data goes in separate migrations from schema changes (easier to re-run individually)

## For the AgentMarket schema specifically
- Every table that has `agent_id` or `buyer_id` or `merchant_id` must have FK
- Every `audit_log` row must have a real `session_id` FK
- `signed_receipts` must FK to both `negotiation_sessions` and `spending_policies`
- `negotiation_sessions.replay_data` is a `jsonb` column — store LLM prompts + model + temperature + seed there
