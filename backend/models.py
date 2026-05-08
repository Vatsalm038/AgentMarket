"""ORM models mirroring migration 365bcb27952f.

Source of truth is the Alembic migration; this file MUST match it. Crypto material
(Ed25519 keys + signatures) is stored as raw BYTEA — base64 encoding only happens
at the API boundary. Embeddings are JSONB float arrays (ADR-009).
"""

import enum
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AgentRole(str, enum.Enum):
    USER_AGENT = "user_agent"
    MERCHANT_AGENT = "merchant_agent"


class TxnStatus(str, enum.Enum):
    PENDING = "pending"
    NEGOTIATING = "negotiating"
    SETTLED = "settled"
    REJECTED = "rejected"
    REVOKED = "revoked"


# create_type=False because the migration already creates the PG ENUM types;
# letting SQLAlchemy try to create them again at metadata.create_all time would error.
_AGENT_ROLE = Enum(AgentRole, name="agent_role", create_type=False, native_enum=True,
                   values_callable=lambda x: [e.value for e in x])
_TXN_STATUS = Enum(TxnStatus, name="txn_status", create_type=False, native_enum=True,
                   values_callable=lambda x: [e.value for e in x])


class Agent(Base):
    __tablename__ = "agents"
    id = Column(String, primary_key=True)
    role = Column(_AGENT_ROLE, nullable=False)
    public_key = Column(LargeBinary, nullable=False)
    owner_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True),
                        server_default=text("now()"), nullable=False)

    __table_args__ = (
        CheckConstraint("octet_length(public_key) = 32",
                        name="agents_pubkey_ed25519_len"),
        Index("ix_agents_owner_id", "owner_id"),
    )


class Merchant(Base):
    __tablename__ = "merchants"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(Text, nullable=False)
    city = Column(String, nullable=False)
    pincode = Column(String(10), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=text("now()"), nullable=False)

    __table_args__ = (
        Index("ix_merchants_city", "city"),
        Index("ix_merchants_pincode", "pincode"),
    )


class AgentSkill(Base):
    __tablename__ = "agent_skills"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=False)
    system_prompt_template = Column(Text, nullable=False)
    params = Column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
    created_at = Column(DateTime(timezone=True),
                        server_default=text("now()"), nullable=False)


class MerchantAgent(Base):
    __tablename__ = "merchant_agents"
    id = Column(String, primary_key=True)
    merchant_id = Column(String,
                         ForeignKey("merchants.id", ondelete="CASCADE"),
                         nullable=False)
    public_key = Column(LargeBinary, nullable=False)
    skill_id = Column(String,
                      ForeignKey("agent_skills.id", ondelete="RESTRICT"),
                      nullable=False)
    created_at = Column(DateTime(timezone=True),
                        server_default=text("now()"), nullable=False)

    __table_args__ = (
        CheckConstraint("octet_length(public_key) = 32",
                        name="merchant_agents_pubkey_ed25519_len"),
        Index("ix_merchant_agents_merchant_id", "merchant_id"),
    )


class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True)
    merchant_id = Column(String,
                         ForeignKey("merchants.id", ondelete="CASCADE"),
                         nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    listed_price = Column(Numeric(12, 2), nullable=False)
    floor_price = Column(Numeric(12, 2), nullable=False)
    category = Column(String, nullable=False)
    embedding = Column(JSONB, nullable=True)
    embedding_model = Column(String, nullable=True)
    embedding_generated_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, server_default=text("true"), nullable=False)
    created_at = Column(DateTime(timezone=True),
                        server_default=text("now()"), nullable=False)

    __table_args__ = (
        CheckConstraint("floor_price <= listed_price",
                        name="products_floor_le_listed"),
        CheckConstraint("listed_price > 0", name="products_listed_positive"),
        Index("ix_products_merchant_id", "merchant_id"),
        Index("ix_products_is_active", "is_active"),
    )


class SpendingPolicy(Base):
    __tablename__ = "spending_policies"
    id = Column(String, primary_key=True)
    agent_id = Column(String,
                      ForeignKey("agents.id", ondelete="CASCADE"),
                      nullable=False)
    max_per_txn = Column(Numeric(12, 2), nullable=False)
    max_per_day = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), server_default=text("'INR'"), nullable=False)
    allow_auto_renew = Column(Boolean,
                              server_default=text("false"), nullable=False)
    categories = Column(Text, server_default=text("'*'"), nullable=False)
    signed_payload = Column(LargeBinary, nullable=False)
    signature = Column(LargeBinary, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=text("now()"), nullable=False)

    __table_args__ = (
        CheckConstraint("octet_length(signature) = 64",
                        name="policies_sig_ed25519_len"),
        CheckConstraint("max_per_txn > 0",
                        name="policies_max_per_txn_positive"),
        CheckConstraint("max_per_day >= max_per_txn",
                        name="policies_day_ge_txn"),
        Index("ix_spending_policies_agent_active", "agent_id", "revoked_at"),
    )


class NegotiationSession(Base):
    __tablename__ = "negotiation_sessions"
    id = Column(String, primary_key=True)
    buyer_agent_id = Column(String,
                            ForeignKey("agents.id", ondelete="RESTRICT"),
                            nullable=False)
    merchant_agent_id = Column(String,
                               ForeignKey("merchant_agents.id", ondelete="RESTRICT"),
                               nullable=False)
    product_id = Column(String,
                        ForeignKey("products.id", ondelete="RESTRICT"),
                        nullable=False)
    policy_id = Column(String,
                       ForeignKey("spending_policies.id", ondelete="RESTRICT"),
                       nullable=False)
    item = Column(String, nullable=False)
    listed_price = Column(Numeric(12, 2), nullable=False)
    final_price = Column(Numeric(12, 2), nullable=True)
    rounds = Column(JSONB, server_default=text("'[]'::jsonb"), nullable=False)
    status = Column(_TXN_STATUS,
                    server_default=text("'pending'::txn_status"), nullable=False)
    replay_data = Column(JSONB, nullable=True)
    replay_model = Column(String, nullable=True)
    replay_seed = Column(BigInteger, nullable=True)
    replay_prompt_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=text("now()"), nullable=False)
    settled_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_sessions_status_created", "status", "created_at"),
        Index("ix_sessions_buyer_created", "buyer_agent_id", "created_at"),
    )


class SignedReceipt(Base):
    __tablename__ = "signed_receipts"
    receipt_id = Column(String, primary_key=True)
    session_id = Column(String,
                        ForeignKey("negotiation_sessions.id", ondelete="RESTRICT"),
                        nullable=False, unique=True)
    policy_id = Column(String,
                       ForeignKey("spending_policies.id", ondelete="RESTRICT"),
                       nullable=False)
    buyer_agent_id = Column(String,
                            ForeignKey("agents.id", ondelete="RESTRICT"),
                            nullable=False)
    merchant_agent_id = Column(String,
                               ForeignKey("merchant_agents.id", ondelete="RESTRICT"),
                               nullable=False)
    amount_inr = Column(Numeric(12, 2), nullable=False)
    payload_json = Column(JSONB, nullable=False)
    signed_payload = Column(LargeBinary, nullable=False)
    agent_signature = Column(LargeBinary, nullable=False)
    razorpay_order_id = Column(String, nullable=True)
    razorpay_payment_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=text("now()"), nullable=False)

    __table_args__ = (
        CheckConstraint("octet_length(agent_signature) = 64",
                        name="receipts_sig_ed25519_len"),
        CheckConstraint("amount_inr > 0", name="receipts_amount_positive"),
        Index("ix_receipts_buyer_created",
              "buyer_agent_id", text("created_at DESC")),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(UUID(as_uuid=True),
                server_default=text("gen_random_uuid()"),
                primary_key=True, default=uuid.uuid4)
    session_id = Column(String,
                        ForeignKey("negotiation_sessions.id", ondelete="CASCADE"),
                        nullable=False)
    agent_id = Column(String, nullable=False)
    event = Column(String, nullable=False)
    payload = Column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)
    timestamp = Column(DateTime(timezone=True),
                       server_default=text("now()"), nullable=False)

    __table_args__ = (
        Index("ix_audit_session_ts", "session_id", "timestamp"),
    )


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    # Composite PK (endpoint, key) — there is no agent_id column, so a key
    # presented under one endpoint cannot collide with the same key under another,
    # but two callers that share a key on the same endpoint will collide. Per-agent
    # scoping is a 1.7+ concern.
    endpoint = Column(String, nullable=False)
    key = Column(String, nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_json = Column(JSONB, nullable=True)
    status_code = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=text("now()"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("endpoint", "key"),
        Index("ix_idempotency_expires_at", "expires_at"),
    )
