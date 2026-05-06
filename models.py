from sqlalchemy import Column, String, Float, DateTime, Text, Boolean, Enum
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum

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

class Agent(Base):
    __tablename__ = "agents"
    id = Column(String, primary_key=True)          # DID-style: did:agent:<uuid>
    role = Column(Enum(AgentRole), nullable=False)
    public_key = Column(Text, nullable=False)       # PEM public key
    owner_id = Column(String, nullable=False)       # human owner
    created_at = Column(DateTime, default=datetime.utcnow)

class SpendingPolicy(Base):
    __tablename__ = "spending_policies"
    id = Column(String, primary_key=True)
    agent_id = Column(String, nullable=False)
    max_per_txn = Column(Float, nullable=False)     # max per single transaction
    max_per_day = Column(Float, nullable=False)     # daily cap
    currency = Column(String, default="INR")
    allow_auto_renew = Column(Boolean, default=False)
    categories = Column(Text, default="*")          # comma-separated or "*"
    signature = Column(Text, nullable=False)        # signed by human owner
    created_at = Column(DateTime, default=datetime.utcnow)

class NegotiationSession(Base):
    __tablename__ = "negotiation_sessions"
    id = Column(String, primary_key=True)
    buyer_agent_id = Column(String, nullable=False)
    merchant_agent_id = Column(String, nullable=False)
    item = Column(String, nullable=False)
    initial_price = Column(Float, nullable=False)
    final_price = Column(Float, nullable=True)
    rounds = Column(Text, default="[]")             # JSON array of round details
    status = Column(Enum(TxnStatus), default=TxnStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    settled_at = Column(DateTime, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False)
    agent_id = Column(String, nullable=False)
    event = Column(String, nullable=False)          # e.g. "offer_sent", "payment_settled"
    payload = Column(Text, nullable=False)          # JSON
    timestamp = Column(DateTime, default=datetime.utcnow)
