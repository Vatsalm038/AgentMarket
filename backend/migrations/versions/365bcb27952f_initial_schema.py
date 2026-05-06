"""initial schema

Revision ID: 365bcb27952f
Revises:
Create Date: 2026-05-07

Drops the prototype RSA-era schema and creates the Agent Market schema:
agents, spending_policies, merchants, agent_skills, merchant_agents,
products, negotiation_sessions, signed_receipts, audit_log, idempotency_keys.

All Ed25519 keys/signatures are stored as BYTEA with octet-length CHECKs
(ADR-001). Embeddings are JSONB float arrays (ADR-009 — pgvector deferred).
All timestamps are TIMESTAMPTZ.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "365bcb27952f"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


AGENT_ROLE = postgresql.ENUM(
    "user_agent", "merchant_agent", name="agent_role", create_type=False
)
TXN_STATUS = postgresql.ENUM(
    "pending", "negotiating", "settled", "rejected", "revoked",
    name="txn_status", create_type=False,
)


def upgrade() -> None:
    # gen_random_uuid() is built-in from PG 13; pgcrypto provides it on PG 12.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Drop prototype tables if they exist (fresh DB but be defensive).
    for t in ("audit_log", "negotiation_sessions", "spending_policies", "agents"):
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    op.execute("DROP TYPE IF EXISTS agent_role CASCADE")
    op.execute("DROP TYPE IF EXISTS txn_status CASCADE")

    AGENT_ROLE.create(op.get_bind(), checkfirst=True)
    TXN_STATUS.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "agents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("role", AGENT_ROLE, nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.CheckConstraint(
            "octet_length(public_key) = 32", name="agents_pubkey_ed25519_len",
        ),
    )
    op.create_index("ix_agents_owner_id", "agents", ["owner_id"])

    op.create_table(
        "merchants",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("pincode", sa.String(length=10), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
    )
    op.create_index("ix_merchants_city", "merchants", ["city"])
    op.create_index("ix_merchants_pincode", "merchants", ["pincode"])

    op.create_table(
        "agent_skills",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("system_prompt_template", sa.Text(), nullable=False),
        sa.Column(
            "params", postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"), nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
    )

    op.create_table(
        "merchant_agents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "merchant_id", sa.String(),
            sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column(
            "skill_id", sa.String(),
            sa.ForeignKey("agent_skills.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.CheckConstraint(
            "octet_length(public_key) = 32",
            name="merchant_agents_pubkey_ed25519_len",
        ),
    )
    op.create_index("ix_merchant_agents_merchant_id", "merchant_agents", ["merchant_id"])

    op.create_table(
        "products",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "merchant_id", sa.String(),
            sa.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("listed_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("floor_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding_model", sa.String(), nullable=True),
        sa.Column("embedding_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(),
            server_default=sa.text("true"), nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.CheckConstraint(
            "floor_price <= listed_price", name="products_floor_le_listed",
        ),
        sa.CheckConstraint("listed_price > 0", name="products_listed_positive"),
    )
    op.create_index("ix_products_merchant_id", "products", ["merchant_id"])
    op.create_index("ix_products_is_active", "products", ["is_active"])

    op.create_table(
        "spending_policies",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "agent_id", sa.String(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("max_per_txn", sa.Numeric(12, 2), nullable=False),
        sa.Column("max_per_day", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "currency", sa.String(length=3),
            server_default=sa.text("'INR'"), nullable=False,
        ),
        sa.Column(
            "allow_auto_renew", sa.Boolean(),
            server_default=sa.text("false"), nullable=False,
        ),
        sa.Column(
            "categories", sa.Text(),
            server_default=sa.text("'*'"), nullable=False,
        ),
        # The exact bytes that were signed — needed to re-verify without
        # reconstructing canonical JSON from columns.
        sa.Column("signed_payload", sa.LargeBinary(), nullable=False),
        sa.Column("signature", sa.LargeBinary(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.CheckConstraint(
            "octet_length(signature) = 64", name="policies_sig_ed25519_len",
        ),
        sa.CheckConstraint("max_per_txn > 0", name="policies_max_per_txn_positive"),
        sa.CheckConstraint("max_per_day >= max_per_txn", name="policies_day_ge_txn"),
    )
    op.create_index(
        "ix_spending_policies_agent_active", "spending_policies",
        ["agent_id", "revoked_at"],
    )

    op.create_table(
        "negotiation_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "buyer_agent_id", sa.String(),
            sa.ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "merchant_agent_id", sa.String(),
            sa.ForeignKey("merchant_agents.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "product_id", sa.String(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "policy_id", sa.String(),
            sa.ForeignKey("spending_policies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("item", sa.String(), nullable=False),
        sa.Column("listed_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("final_price", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "rounds", postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"), nullable=False,
        ),
        sa.Column(
            "status", TXN_STATUS,
            server_default=sa.text("'pending'::txn_status"), nullable=False,
        ),
        # Replay (ADR-007). Full data in JSONB; flat columns for fast filtering.
        sa.Column("replay_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("replay_model", sa.String(), nullable=True),
        sa.Column("replay_seed", sa.BigInteger(), nullable=True),
        sa.Column("replay_prompt_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_sessions_status_created", "negotiation_sessions",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_sessions_buyer_created", "negotiation_sessions",
        ["buyer_agent_id", "created_at"],
    )

    op.create_table(
        "signed_receipts",
        sa.Column("receipt_id", sa.String(), primary_key=True),
        sa.Column(
            "session_id", sa.String(),
            sa.ForeignKey("negotiation_sessions.id", ondelete="RESTRICT"),
            nullable=False, unique=True,
        ),
        sa.Column(
            "policy_id", sa.String(),
            sa.ForeignKey("spending_policies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "buyer_agent_id", sa.String(),
            sa.ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "merchant_agent_id", sa.String(),
            sa.ForeignKey("merchant_agents.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("amount_inr", sa.Numeric(12, 2), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("signed_payload", sa.LargeBinary(), nullable=False),
        sa.Column("agent_signature", sa.LargeBinary(), nullable=False),
        sa.Column("razorpay_order_id", sa.String(), nullable=True),
        sa.Column("razorpay_payment_id", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.CheckConstraint(
            "octet_length(agent_signature) = 64",
            name="receipts_sig_ed25519_len",
        ),
        sa.CheckConstraint("amount_inr > 0", name="receipts_amount_positive"),
    )
    op.create_index(
        "ix_receipts_buyer_created", "signed_receipts",
        ["buyer_agent_id", sa.text("created_at DESC")],
    )

    op.create_table(
        "audit_log",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column(
            "session_id", sa.String(),
            sa.ForeignKey("negotiation_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_id", sa.String(), nullable=False),
        sa.Column("event", sa.String(), nullable=False),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"), nullable=False,
        ),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
    )
    op.create_index("ix_audit_session_ts", "audit_log", ["session_id", "timestamp"])

    op.create_table(
        "idempotency_keys",
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("endpoint", "key"),
    )
    op.create_index("ix_idempotency_expires_at", "idempotency_keys", ["expires_at"])


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_table("audit_log")
    op.drop_table("signed_receipts")
    op.drop_table("negotiation_sessions")
    op.drop_table("spending_policies")
    op.drop_table("products")
    op.drop_table("merchant_agents")
    op.drop_table("agent_skills")
    op.drop_table("merchants")
    op.drop_table("agents")
    op.execute("DROP TYPE IF EXISTS txn_status")
    op.execute("DROP TYPE IF EXISTS agent_role")
