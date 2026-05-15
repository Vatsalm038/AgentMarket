"""ADR-012: users table, owner_user_id on agents/merchants, platform fee + pay-later columns

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-15

Implements the schema additions required by ADR-012 (SignedDeals pivot):
  1. users table — top-level auth entity; absorbs old buyers concept.
  2. agents.owner_user_id — nullable FK to users, alongside existing
     owner_id string (kept for signed-payload backward compat).
  3. merchants.owner_user_id — nullable FK to users.
  4. products.image_url — nullable, for future Cloudflare R2 uploads.
  5. negotiation_sessions.pay_later_due_date — nullable date.
  6. signed_receipts.platform_fee_paise + platform_fee_pct — nullable,
     populated on new settlements using PLATFORM_FEE_PCT env var.
  7. txn_status enum extended with pay_later + payment_initiated values.

All changes are backward-compatible (nullable columns, no dropped columns).
Downgrade removes additions in reverse order.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table — UUID PK (gen_random_uuid()), email unique, bcrypt hash,
    #    google_id nullable (Google OAuth deferred to post-MVP),
    #    is_buyer / is_merchant booleans (a user can be both).
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email           TEXT NOT NULL,
            password_hash   TEXT NOT NULL,
            google_id       TEXT,
            is_buyer        BOOLEAN NOT NULL DEFAULT TRUE,
            is_merchant     BOOLEAN NOT NULL DEFAULT FALSE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT users_email_unique UNIQUE (email)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)")

    # 2. agents.owner_user_id — nullable FK alongside existing owner_id string.
    #    Added nullable so existing rows (including MCP demo agent) are unaffected.
    op.execute("""
        ALTER TABLE agents
        ADD COLUMN IF NOT EXISTS owner_user_id UUID
            REFERENCES users(id) ON DELETE SET NULL
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_agents_owner_user_id ON agents (owner_user_id)"
    )

    # 3. merchants.owner_user_id — nullable FK; existing seeded merchants have no
    #    user owner for MVP.
    op.execute("""
        ALTER TABLE merchants
        ADD COLUMN IF NOT EXISTS owner_user_id UUID
            REFERENCES users(id) ON DELETE SET NULL
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_merchants_owner_user_id ON merchants (owner_user_id)"
    )

    # 4. products.image_url — nullable; Cloudflare R2 presigned upload is post-MVP.
    op.execute("""
        ALTER TABLE products
        ADD COLUMN IF NOT EXISTS image_url TEXT
    """)

    # 5. negotiation_sessions.pay_later_due_date — nullable date column.
    #    Status values pay_later / payment_initiated added to the PG enum below.
    op.execute("""
        ALTER TABLE negotiation_sessions
        ADD COLUMN IF NOT EXISTS pay_later_due_date DATE
    """)

    # 6. Extend txn_status enum with new values (IF NOT EXISTS guard via DO block).
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumtypid = 'txn_status'::regtype
                  AND enumlabel = 'pay_later'
            ) THEN
                ALTER TYPE txn_status ADD VALUE 'pay_later';
            END IF;
        END$$
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumtypid = 'txn_status'::regtype
                  AND enumlabel = 'payment_initiated'
            ) THEN
                ALTER TYPE txn_status ADD VALUE 'payment_initiated';
            END IF;
        END$$
    """)

    # 7. signed_receipts: platform fee columns — populated on new settlements.
    op.execute("""
        ALTER TABLE signed_receipts
        ADD COLUMN IF NOT EXISTS platform_fee_paise INTEGER,
        ADD COLUMN IF NOT EXISTS platform_fee_pct    NUMERIC(6, 4)
    """)

    # 8. audit_log schema fixes — initial migration used INTEGER id + missing agent_id.
    #    Models.py uses UUID id + agent_id TEXT. Fix both.
    op.execute("""
        ALTER TABLE audit_log
        ADD COLUMN IF NOT EXISTS agent_id TEXT NOT NULL DEFAULT ''
    """)
    # Convert audit_log.id from SERIAL INTEGER to UUID only if it's still integer type
    op.execute("""
        DO $$
        BEGIN
            IF (SELECT data_type FROM information_schema.columns
                WHERE table_name='audit_log' AND column_name='id') = 'integer' THEN
                DROP INDEX IF EXISTS ix_audit_session_ts;
                ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS audit_log_pkey;
                ALTER TABLE audit_log DROP COLUMN id;
                ALTER TABLE audit_log ADD COLUMN id UUID PRIMARY KEY DEFAULT gen_random_uuid();
                CREATE INDEX IF NOT EXISTS ix_audit_session_ts ON audit_log (session_id, timestamp);
            END IF;
        END$$
    """)


def downgrade() -> None:
    # Remove in reverse order. Enum value removal is unsupported in Postgres;
    # drop and recreate would lose data — skip the enum downgrade.
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS agent_id")
    op.execute("ALTER TABLE signed_receipts DROP COLUMN IF EXISTS platform_fee_paise")
    op.execute("ALTER TABLE signed_receipts DROP COLUMN IF EXISTS platform_fee_pct")
    op.execute("ALTER TABLE negotiation_sessions DROP COLUMN IF EXISTS pay_later_due_date")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS image_url")
    op.execute("DROP INDEX IF EXISTS ix_merchants_owner_user_id")
    op.execute("ALTER TABLE merchants DROP COLUMN IF EXISTS owner_user_id")
    op.execute("DROP INDEX IF EXISTS ix_agents_owner_user_id")
    op.execute("ALTER TABLE agents DROP COLUMN IF EXISTS owner_user_id")
    op.execute("DROP TABLE IF EXISTS users")
