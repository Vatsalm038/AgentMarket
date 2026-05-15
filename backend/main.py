"""
Main FastAPI application — Agentic Commerce Protocol (SignedDeals, ADR-012)
Endpoints:
  POST /auth/register             — register user (email + password → JWT)
  POST /auth/login                — login → JWT
  GET  /auth/me                   — decode current JWT claims
  POST /agents/register           — register a new agent
  POST /agents/delegate           — owner signs spending policy
  GET  /agents/{id}/spend         — get agent's daily spend summary
  GET  /agents/{id}/pubkey        — fetch agent's Ed25519 public key
  GET  /.well-known/platform-pubkey — platform's Ed25519 public key
  POST /commerce/negotiate        — run single negotiation session (Idempotency-Key required)
  POST /commerce/auction          — run multi-merchant auction       (Idempotency-Key required)
  GET  /commerce/sessions         — list all sessions
  GET  /commerce/session/{id}     — session detail + audit log
  POST /commerce/checkout/{id}    — create Razorpay order for settled session (Idempotency-Key required)
  POST /commerce/revoke/{id}      — revoke/cancel a session
  POST /webhooks/razorpay         — receive Razorpay payment webhook events
  WS   /ws/session/{id}           — real-time session event stream
  GET  /health                    — health check
"""

import asyncio
import base64
import enum
import hashlib
import hmac
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization as _ser
from cryptography.hazmat.primitives.asymmetric import ed25519 as _ed
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from auction import run_auction
from database import get_db, init_db
from identity import (create_agent_credential, generate_agent_id, generate_keypair,
                      sign_policy, validate_spend, verify_policy_signature)
from models import (Agent, AgentRole, AgentSkill, AuditLog, IdempotencyKey, Merchant,
                    MerchantAgent, NegotiationSession, Product,
                    SignedReceipt, SpendingPolicy, TxnStatus, User)
from auth import UserPayload, create_access_token, get_current_user, hash_password, verify_password
from api.merchant_routes import router as merchant_router
from api.buyer_routes import router as buyer_router
from negotiation import run_negotiation
from razorpay_settlement import (settle_via_razorpay, create_razorpay_order,
                                 RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET,
                                 RAZORPAY_AVAILABLE)
from settlement import _canonical_bytes, build_audit_log, create_transaction
from spend_tracker import get_daily_spent, get_spend_summary


# Placeholder merchant/product fixtures used until 1.6 seeds real data.
# Sessions and receipts have NOT NULL FKs into merchant_agents/products; without
# real seed rows those inserts would fail. These rows are deterministic so
# repeated startups are idempotent.
_PLACEHOLDER_MERCHANT_ID = "mer_placeholder"
_PLACEHOLDER_SKILL_ID = "skl_placeholder"
_PLACEHOLDER_MERCHANT_AGENT_ID = "did:merchant:placeholder000000000000000000000"
_PLACEHOLDER_PRODUCT_ID = "prd_placeholder"


# WebSocket subscriber queues keyed by session_id. Each connected client gets
# its own asyncio.Queue so _ws_publish can fan-out without blocking.
_session_subscribers: dict[str, set[asyncio.Queue]] = {}


# Platform Ed25519 keypair lives only in process memory (CLAUDE.md rule 7).
# Loaded at startup from PLATFORM_PRIVATE_KEY_B64; if absent, generated and
# logged so the operator can pin a stable value across restarts. Never persisted.
_PLATFORM_PUB_B64: str | None = None
_PLATFORM_ISSUED_AT: str | None = None
_PLATFORM_SOURCE: str | None = None


async def _ws_publish(session_id: str, event: dict) -> None:
    """Fan-out an event dict to every queue subscribed to session_id.

    Fire-and-forget: callers wrap with asyncio.create_task so they never
    block the HTTP response path waiting for slow WebSocket consumers."""
    for q in list(_session_subscribers.get(session_id, set())):
        await q.put(event)


async def _ws_subscribe(session_id: str) -> asyncio.Queue:
    """Register a new per-client queue and return it."""
    q: asyncio.Queue = asyncio.Queue()
    _session_subscribers.setdefault(session_id, set()).add(q)
    return q


def _ws_unsubscribe(session_id: str, q: asyncio.Queue) -> None:
    """Remove a client queue; clean up the session key when empty."""
    subscribers = _session_subscribers.get(session_id)
    if subscribers:
        subscribers.discard(q)
        if not subscribers:
            _session_subscribers.pop(session_id, None)


def _load_platform_keypair() -> None:
    global _PLATFORM_PUB_B64, _PLATFORM_ISSUED_AT, _PLATFORM_SOURCE
    env_priv = os.getenv("PLATFORM_PRIVATE_KEY_B64")
    if env_priv:
        try:
            priv = _ed.Ed25519PrivateKey.from_private_bytes(base64.b64decode(env_priv))
            source = "env"
        except (ValueError, TypeError) as exc:
            raise RuntimeError(f"PLATFORM_PRIVATE_KEY_B64 is malformed: {exc}") from exc
    else:
        priv = _ed.Ed25519PrivateKey.generate()
        priv_raw = priv.private_bytes(
            encoding=_ser.Encoding.Raw, format=_ser.PrivateFormat.Raw,
            encryption_algorithm=_ser.NoEncryption(),
        )
        logger.warning(
            "PLATFORM_PRIVATE_KEY_B64 unset — generated an ephemeral platform "
            "keypair. Pin it across restarts by setting "
            "PLATFORM_PRIVATE_KEY_B64=%s", base64.b64encode(priv_raw).decode(),
        )
        source = "ephemeral"
    pub_raw = priv.public_key().public_bytes(
        encoding=_ser.Encoding.Raw, format=_ser.PublicFormat.Raw,
    )
    _PLATFORM_PUB_B64 = base64.b64encode(pub_raw).decode()
    _PLATFORM_ISSUED_AT = datetime.now(timezone.utc).isoformat()
    _PLATFORM_SOURCE = source


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    _load_platform_keypair()
    yield


app = FastAPI(
    title="Agentic Commerce Protocol",
    description="A2A negotiation, identity delegation, and payment settlement for AI agents",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(merchant_router)
app.include_router(buyer_router)


# ── Pydantic models ─────────────────────────────────────────────────────────

class RegisterAgentRequest(BaseModel):
    owner_id: str
    role: str = "user_agent"
    owner_user_id: str | None = None  # set by frontend when user is authenticated


class DelegateRequest(BaseModel):
    agent_id: str
    owner_private_key: str  # base64(raw 32-byte Ed25519 private key)
    owner_public_key: str   # base64(raw 32-byte Ed25519 public key)
    max_per_txn: float
    max_per_day: float
    currency: str = "INR"
    allow_auto_renew: bool = False
    categories: str = "*"


class NegotiateRequest(BaseModel):
    buyer_agent_id: str
    agent_private_key: str
    item: str
    listed_price: float
    initial_offer: float
    use_razorpay: bool = False


class AuctionRequest(BaseModel):
    buyer_agent_id: str
    agent_private_key: str
    anchor_product_id: str  # caller pre-resolves intent → product (matcher in 2.1)
    num_merchants: int = 3
    buyer_priorities: str = "lowest price"
    use_razorpay: bool = True
    max_budget_inr: float | None = None  # buyer's UI max price — caps policy_max


class RevokeRequest(BaseModel):
    owner_id: str
    reason: str = "Revoked by owner"


# ADR-012 auth request/response models
class AuthRegisterRequest(BaseModel):
    email: str
    password: str
    is_buyer: bool = True
    is_merchant: bool = False


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    is_buyer: bool
    is_merchant: bool


# ── Helpers ─────────────────────────────────────────────────────────────────

def _payload_hash(body: BaseModel) -> str:
    """SHA-256 of canonical JSON of a Pydantic body. Sort_keys + tight separators
    make the digest order- and whitespace-independent so callers comparing the
    same logical request always get the same hash."""
    canonical = _canonical_bytes(body.model_dump())
    return hashlib.sha256(canonical).hexdigest()


async def _ensure_placeholder_fixtures(db: AsyncSession) -> tuple[str, str]:
    """Ensure placeholder merchant/skill/merchant_agent/product rows exist so that
    NegotiationSession and SignedReceipt FKs resolve. Returns (merchant_agent_id,
    product_id). Will be replaced by real seed data in 1.6 and by matcher-driven
    selection in 1.7.

    Each insert uses ON CONFLICT DO NOTHING so concurrent callers can race the
    "first time" path without one of them tripping a PK violation. This is a
    stopgap until 1.6 seeds real fixtures at startup.
    """
    await db.execute(
        pg_insert(Merchant.__table__).values(
            id=_PLACEHOLDER_MERCHANT_ID, name="Placeholder Merchant",
            address="-", city="Mumbai", pincode="400001", lat=19.0760, lng=72.8777,
        ).on_conflict_do_nothing(index_elements=["id"])
    )
    await db.execute(
        pg_insert(AgentSkill.__table__).values(
            id=_PLACEHOLDER_SKILL_ID, name="placeholder",
            description="Placeholder skill until 1.8 seeds real personas.",
            system_prompt_template="You are a merchant.",
        ).on_conflict_do_nothing(index_elements=["id"])
    )
    # Stub Ed25519 public key — 32 zero bytes is a valid octet length and
    # satisfies the CHECK constraint. Real merchant keys arrive in 1.6.
    await db.execute(
        pg_insert(MerchantAgent.__table__).values(
            id=_PLACEHOLDER_MERCHANT_AGENT_ID,
            merchant_id=_PLACEHOLDER_MERCHANT_ID,
            public_key=b"\x00" * 32,
            skill_id=_PLACEHOLDER_SKILL_ID,
        ).on_conflict_do_nothing(index_elements=["id"])
    )
    await db.execute(
        pg_insert(Product.__table__).values(
            id=_PLACEHOLDER_PRODUCT_ID, merchant_id=_PLACEHOLDER_MERCHANT_ID,
            name="Placeholder Product", listed_price=1.00, floor_price=1.00,
            category="placeholder",
        ).on_conflict_do_nothing(index_elements=["id"])
    )
    await db.flush()
    return _PLACEHOLDER_MERCHANT_AGENT_ID, _PLACEHOLDER_PRODUCT_ID


class _IdempotencyDecision(str, enum.Enum):
    MISS = "miss"
    HIT_REPLAY = "hit_replay"
    HIT_MISMATCH = "hit_mismatch"
    HIT_PENDING = "hit_pending"


def _idempotency_decide(stored: IdempotencyKey | None, incoming_hash: str) -> _IdempotencyDecision:
    """Pure decision function so the four-branch logic is testable without a DB."""
    if stored is None:
        return _IdempotencyDecision.MISS
    if stored.request_hash != incoming_hash:
        return _IdempotencyDecision.HIT_MISMATCH
    # NULL response_json is the in-flight sentinel — the column is nullable in
    # the migration, so we use NULL rather than introducing a status column.
    if stored.response_json is None:
        return _IdempotencyDecision.HIT_PENDING
    return _IdempotencyDecision.HIT_REPLAY


async def _idempotency_claim(
    db: AsyncSession, endpoint: str, key: str, request_hash: str
) -> bool:
    """Atomically reserve (endpoint, key) with NULL response_json as the pending
    marker. Returns True if THIS caller claimed the row; False if a row already
    exists (caller must SELECT and decide replay/mismatch/pending).

    INSERT ... ON CONFLICT DO NOTHING is the atomic claim — two concurrent callers
    cannot both succeed, so only one runs the negotiation."""
    stmt = (
        pg_insert(IdempotencyKey.__table__)
        .values(
            endpoint=endpoint, key=key, request_hash=request_hash,
            response_json=None, status_code=None,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        .on_conflict_do_nothing(index_elements=["endpoint", "key"])
    )
    result = await db.execute(stmt)
    return result.rowcount == 1


async def _idempotency_replay_or_409(
    db: AsyncSession, endpoint: str, key: str, request_hash: str,
) -> dict:
    """Read the existing row and translate its state to a response or HTTPException.
    Caller has already failed to claim the key, so a row MUST exist."""
    result = await db.execute(
        select(IdempotencyKey).where(
            IdempotencyKey.endpoint == endpoint, IdempotencyKey.key == key
        )
    )
    row = result.scalar_one_or_none()
    decision = _idempotency_decide(row, request_hash)

    if decision is _IdempotencyDecision.HIT_REPLAY:
        return row.response_json
    if decision is _IdempotencyDecision.HIT_MISMATCH:
        # Log a fingerprint of the key (not the full value) so abuse is observable
        # without DB writes — audit_log.session_id is NOT NULL FK so we can't
        # write there before a session exists.
        logger.warning("idempotency_conflict endpoint=%s key=%s", endpoint, key[:12])
        raise HTTPException(
            status_code=422,
            detail="Idempotency-Key reused with a different request body",
        )
    if decision is _IdempotencyDecision.HIT_PENDING:
        # Another worker still running the same idempotent request — refusing to
        # block or duplicate work is safer than serialising on a row lock.
        raise HTTPException(
            status_code=409,
            detail="Idempotent request still in progress, retry shortly",
        )
    # MISS would mean the row vanished between INSERT-conflict and SELECT, which
    # shouldn't happen within one transaction; treat as 409 to be safe.
    raise HTTPException(status_code=409, detail="Idempotency state inconsistent, retry")


async def _idempotency_finalize(
    db: AsyncSession, endpoint: str, key: str,
    response_body: dict, status_code: int = 200,
) -> None:
    """Write the real response into the previously-claimed pending row. Caller
    commits afterwards so the work + the finalize land atomically."""
    await db.execute(
        update(IdempotencyKey)
        .where(IdempotencyKey.endpoint == endpoint, IdempotencyKey.key == key)
        .values(response_json=response_body, status_code=status_code)
    )


async def load_agent_and_credential(agent_id: str, db: AsyncSession):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    pol_result = await db.execute(
        select(SpendingPolicy)
        .where(SpendingPolicy.agent_id == agent_id,
               SpendingPolicy.revoked_at.is_(None))
        .order_by(SpendingPolicy.created_at.desc())
    )
    sp = pol_result.scalars().first()
    if not sp:
        raise HTTPException(status_code=400, detail="No active spending policy for agent")

    policy = {
        "agent_id": sp.agent_id,
        "max_per_txn": float(sp.max_per_txn),
        "max_per_day": float(sp.max_per_day),
        "currency": sp.currency,
        "allow_auto_renew": sp.allow_auto_renew,
        "categories": sp.categories,
    }
    signature_b64 = base64.b64encode(sp.signature).decode()
    credential = create_agent_credential(
        agent_id, agent.owner_id, sp.id, policy, signature_b64
    )
    return agent, sp, credential


async def save_session_and_audit(
    session: dict, credential: dict, policy_id: str,
    merchant_agent_id: str, product_id: str,
    agent_private_key: str, db: AsyncSession,
    use_razorpay: bool = False,
):
    settled = session["status"] == "settled"
    ns = NegotiationSession(
        id=session["session_id"],
        buyer_agent_id=credential["agent_id"],
        merchant_agent_id=merchant_agent_id,
        product_id=product_id,
        policy_id=policy_id,
        item=session["item"],
        listed_price=session["listed_price"],
        final_price=session.get("final_price"),
        rounds=session.get("rounds", []),
        status=TxnStatus(session["status"]),
        settled_at=datetime.now(timezone.utc) if settled else None,
    )
    db.add(ns)
    await db.flush()

    transaction = None
    razorpay_receipt = None

    if settled:
        transaction, signed_bytes = create_transaction(
            session, credential, agent_private_key
        )
        if use_razorpay:
            razorpay_receipt = settle_via_razorpay(session, credential)

        signature_raw = base64.b64decode(transaction["agent_signature"])
        # payload_json must be a JSON-safe dict; the in-memory transaction is.
        db.add(SignedReceipt(
            receipt_id=f"rcpt_{uuid.uuid4().hex[:16]}",
            session_id=ns.id,
            policy_id=policy_id,
            buyer_agent_id=credential["agent_id"],
            merchant_agent_id=merchant_agent_id,
            amount_inr=transaction["amount"],
            payload_json=transaction,
            signed_payload=signed_bytes,
            agent_signature=signature_raw,
            razorpay_order_id=(razorpay_receipt or {}).get("razorpay_order_id"),
            razorpay_payment_id=(razorpay_receipt or {}).get("razorpay_payment_id"),
        ))

    logs = build_audit_log(session, transaction)
    for entry in logs:
        db.add(AuditLog(
            session_id=session["session_id"],
            agent_id=credential["agent_id"],
            event=entry["event"],
            payload=entry["payload"],
        ))

    # Notify any live WebSocket subscribers about the final session status.
    asyncio.create_task(_ws_publish(session["session_id"], {
        "type": "session_update",
        "session_id": session["session_id"],
        "status": session["status"],
        "final_price": session.get("final_price"),
    }))

    # No commit here — the outer endpoint commits once after _idempotency_finalize
    # so the work and the idempotency UPDATE either both land or both roll back.
    await db.flush()
    return transaction, razorpay_receipt, logs


# ── Endpoints ───────────────────────────────────────────────────────────────

# ── /auth ────────────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=AuthTokenResponse, status_code=201)
async def auth_register(req: AuthRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user and return a JWT.

    Email uniqueness is enforced by a DB UNIQUE constraint — concurrent registrations
    with the same email will get a 409. Password is bcrypt-hashed before storage;
    the plain text never touches the DB.
    """
    # Check for existing email first for a clean 409 (rather than a 500 on
    # the unique constraint violation at commit time).
    existing = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        is_buyer=req.is_buyer,
        is_merchant=req.is_merchant,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        is_buyer=user.is_buyer,
        is_merchant=user.is_merchant,
    )
    return AuthTokenResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        is_buyer=user.is_buyer,
        is_merchant=user.is_merchant,
    )


@app.post("/auth/login", response_model=AuthTokenResponse)
async def auth_login(req: AuthLoginRequest, db: AsyncSession = Depends(get_db)):
    """Verify credentials and return a JWT.

    Intentionally returns 401 (not 404) on unknown email to avoid email enumeration.
    """
    user = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        is_buyer=user.is_buyer,
        is_merchant=user.is_merchant,
    )
    return AuthTokenResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        is_buyer=user.is_buyer,
        is_merchant=user.is_merchant,
    )


@app.get("/auth/me", response_model=AuthTokenResponse)
async def auth_me(current_user: UserPayload = Depends(get_current_user)):
    """Return the decoded claims of the current JWT. Useful for frontend bootstrapping."""
    return AuthTokenResponse(
        # access_token is not re-issued here — caller already has it.
        access_token="",
        user_id=current_user.user_id,
        email=current_user.email,
        is_buyer=current_user.is_buyer,
        is_merchant=current_user.is_merchant,
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agentic-commerce-protocol", "version": "1.0.0"}


@app.get("/skills")
async def list_skills(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentSkill).where(AgentSkill.id != "skl_placeholder").order_by(AgentSkill.name)
    )
    skills = result.scalars().all()
    return [{"id": s.id, "name": s.name, "description": s.description} for s in skills]


@app.get("/products/search")
async def search_products(q: str, db: AsyncSession = Depends(get_db)):
    """Case-insensitive text search over product name and description.

    Returns up to 10 active results. Sorted by name so results are stable;
    semantic ranking (embedding cosine) is a post-MVP concern (ADR-009)."""
    from sqlalchemy import or_, case
    results = await db.execute(
        select(Product)
        .where(
            Product.is_active == True,  # noqa: E712
            or_(
                Product.name.ilike(f"%{q}%"),
                Product.description.ilike(f"%{q}%"),
            ),
        )
        # Title matches rank above description-only matches
        .order_by(
            case((Product.name.ilike(f"%{q}%"), 0), else_=1),
            Product.listed_price,
        )
        .limit(10)
    )
    products = results.scalars().all()
    return [
        {
            "id": p.id,
            "title": p.name,
            "description": p.description,
            "listed_price": float(p.listed_price),
            "floor_price": float(p.floor_price),
            "category": p.category,
            "merchant_id": p.merchant_id,
        }
        for p in products
    ]


@app.post("/agents/register")
async def register_agent(req: RegisterAgentRequest, db: AsyncSession = Depends(get_db)):
    agent_id = generate_agent_id()
    private_b64, public_b64 = generate_keypair()
    agent = Agent(
        id=agent_id, role=AgentRole(req.role),
        public_key=base64.b64decode(public_b64),
        owner_id=req.owner_id,
        owner_user_id=req.owner_user_id,
    )
    db.add(agent)
    await db.commit()
    return {
        "agent_id": agent_id,
        "public_key": public_b64,
        "private_key": private_b64,
        "role": req.role,
        "message": "Agent registered. Store private_key securely — not saved on server.",
    }


@app.post("/agents/delegate")
async def delegate_policy(req: DelegateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == req.agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    policy = {
        "agent_id": req.agent_id, "max_per_txn": req.max_per_txn,
        "max_per_day": req.max_per_day, "currency": req.currency,
        "allow_auto_renew": req.allow_auto_renew, "categories": req.categories,
    }

    signature_b64 = sign_policy(req.owner_private_key, policy)
    if not verify_policy_signature(req.owner_public_key, policy, signature_b64):
        raise HTTPException(status_code=400, detail="Policy signature verification failed")

    signed_payload_bytes = _canonical_bytes(policy)
    sp = SpendingPolicy(
        id=f"pol_{uuid.uuid4().hex[:12]}", agent_id=req.agent_id,
        max_per_txn=req.max_per_txn, max_per_day=req.max_per_day,
        currency=req.currency, allow_auto_renew=req.allow_auto_renew,
        categories=req.categories,
        signed_payload=signed_payload_bytes,
        signature=base64.b64decode(signature_b64),
    )
    db.add(sp)
    await db.commit()

    credential = create_agent_credential(
        req.agent_id, agent.owner_id, sp.id, policy, signature_b64
    )
    return {"policy_id": sp.id, "credential": credential,
            "message": "Policy signed and stored. Agent is ready to transact."}


@app.get("/agents/{agent_id}/spend")
async def get_agent_spend(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")
    return await get_spend_summary(agent_id, db)


@app.get("/agents/{agent_id}/pubkey")
async def get_agent_pubkey(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Public-key lookup for receipt verification. Resolves both buyer agents
    (did:agent:*) and merchant agents (did:merchant:*) by DID prefix per ADR-010.
    No auth — public keys are public by definition."""
    if agent_id.startswith("did:merchant:"):
        result = await db.execute(
            select(MerchantAgent).where(MerchantAgent.id == agent_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Merchant agent not found")
        return {
            "agent_id": row.id,
            "public_key": base64.b64encode(row.public_key).decode(),
            "kind": "merchant",
            "registered_at": row.created_at.isoformat(),
        }

    # Default branch is the buyer table; covers did:agent:* and any legacy IDs.
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "agent_id": row.id,
        "public_key": base64.b64encode(row.public_key).decode(),
        "kind": "buyer",
        "registered_at": row.created_at.isoformat(),
    }


@app.get("/.well-known/platform-pubkey")
async def platform_pubkey():
    """Serve the platform-level Ed25519 public key for external verifiers.

    Read-only. Key loaded once at app startup from PLATFORM_PRIVATE_KEY_B64
    (or ephemerally generated in dev). Private key never crosses the wire and
    is never persisted (CLAUDE.md rule 7)."""
    if _PLATFORM_PUB_B64 is None:
        raise HTTPException(status_code=503, detail="Platform key not initialised")
    return {
        "public_key": _PLATFORM_PUB_B64,
        "algorithm": "Ed25519",
        "issued_at": _PLATFORM_ISSUED_AT,
        "kind": "platform",
        "source": _PLATFORM_SOURCE,
    }


@app.post("/commerce/negotiate")
async def negotiate(
    req: NegotiateRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8),
):
    endpoint = "/commerce/negotiate"
    request_hash = _payload_hash(req)

    claimed = await _idempotency_claim(db, endpoint, idempotency_key, request_hash)
    if not claimed:
        cached = await _idempotency_replay_or_409(db, endpoint, idempotency_key, request_hash)
        response.headers["Idempotent-Replay"] = "true"
        return cached

    try:
        agent, sp, credential = await load_agent_and_credential(req.buyer_agent_id, db)
        daily_spent = await get_daily_spent(req.buyer_agent_id, db)

        allowed, reason = validate_spend(credential, req.initial_offer, daily_spent)
        if not allowed:
            raise HTTPException(status_code=400, detail=f"Policy check failed: {reason}")

        merchant_agent_id, product_id = await _ensure_placeholder_fixtures(db)

        session = run_negotiation(
            item=req.item, listed_price=req.listed_price,
            initial_offer=req.initial_offer, credential=credential,
            daily_spent=daily_spent,
        )

        transaction, razorpay_receipt, logs = await save_session_and_audit(
            session, credential, sp.id, merchant_agent_id, product_id,
            req.agent_private_key, db, req.use_razorpay,
        )

        body = {
            "session_id": session["session_id"],
            "status": session["status"],
            "item": req.item,
            "listed_price": req.listed_price,
            "final_price": session.get("final_price"),
            "rounds_count": len(session.get("rounds", [])),
            "transaction": transaction,
            "razorpay_receipt": razorpay_receipt,
            "audit_entries": len(logs),
            "daily_spent_after": daily_spent + (session.get("final_price") or 0),
        }
        await _idempotency_finalize(db, endpoint, idempotency_key, body)
        await db.commit()
        return body
    except Exception:
        # Roll back so the pending claim disappears — caller can retry cleanly.
        await db.rollback()
        raise


@app.post("/commerce/auction")
async def auction(
    req: AuctionRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8),
):
    """Multi-merchant auction — multiple merchants compete, buyer picks best price."""
    endpoint = "/commerce/auction"
    request_hash = _payload_hash(req)

    claimed = await _idempotency_claim(db, endpoint, idempotency_key, request_hash)
    if not claimed:
        cached = await _idempotency_replay_or_409(db, endpoint, idempotency_key, request_hash)
        response.headers["Idempotent-Replay"] = "true"
        return cached

    try:
        agent, sp, credential = await load_agent_and_credential(req.buyer_agent_id, db)
        daily_spent = await get_daily_spent(req.buyer_agent_id, db)

        allowed, reason = validate_spend(credential, 1.0, daily_spent)
        if not allowed:
            raise HTTPException(status_code=400, detail=f"Daily limit reached: {reason}")

        # Cap policy_max to buyer's UI budget so the auction respects what they typed
        if req.max_budget_inr is not None:
            capped = min(float(credential["policy"]["max_per_txn"]), req.max_budget_inr)
            credential = {**credential, "policy": {**credential["policy"], "max_per_txn": capped}}

        result = await run_auction(
            db=db,
            anchor_product_id=req.anchor_product_id,
            credential=credential,
            num_merchants=req.num_merchants,
            buyer_priorities=req.buyer_priorities,
            daily_spent=daily_spent,
        )

        if result["status"] == "settled":
            # The auction selected concrete winner FKs — no placeholder fixtures.
            merchant_agent_id = result["winner_merchant_agent_id"]
            product_id = result["winner_product_id"]
            session_dict = {
                "session_id": result["session_id"],
                "item": result["item"],
                "listed_price": result["listed_price"],
                "initial_offer": result["final_price"],
                "final_price": result["final_price"],
                "rounds": [{"round": 1, "type": "auction",
                            "quotes": result["all_quotes"],
                            "winner": result["winner"],
                            "timestamp": result["created_at"]}],
                "status": "settled",
                "buyer_agent_id": req.buyer_agent_id,
            }
            transaction, razorpay_receipt, logs = await save_session_and_audit(
                session_dict, credential, sp.id, merchant_agent_id, product_id,
                req.agent_private_key, db, req.use_razorpay,
            )
            result["transaction"] = transaction
            result["razorpay_receipt"] = razorpay_receipt
            result["audit_entries"] = len(logs)

            # Persist replay data on the session row (ADR-007). Captured by
            # auction.py and threaded through here so replay_negotiation can
            # re-run the auction with byte-identical prompts/seeds. We avoid
            # broadcasting the full replay payload back in the HTTP response —
            # callers fetch it from /commerce/session/{id} when they need it.
            replay_payload = result.pop("replay_payload", None)
            if replay_payload is not None:
                await db.execute(
                    update(NegotiationSession)
                    .where(NegotiationSession.id == result["session_id"])
                    .values(
                        replay_data=replay_payload,
                        replay_model=replay_payload.get("auction", {}).get("model"),
                        replay_seed=(
                            (replay_payload.get("auction", {}).get("buyer_eval") or {})
                            .get("seed")
                        ),
                    )
                )

        await _idempotency_finalize(db, endpoint, idempotency_key, result)
        await db.commit()
        return result
    except Exception:
        await db.rollback()
        raise


@app.get("/commerce/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NegotiationSession).order_by(NegotiationSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [{"session_id": s.id, "item": s.item, "status": s.status.value,
             "listed_price": float(s.listed_price),
             "final_price": float(s.final_price) if s.final_price is not None else None,
             "buyer_agent_id": s.buyer_agent_id,
             "created_at": s.created_at.isoformat()} for s in sessions]


@app.get("/commerce/session/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    s_result = await db.execute(
        select(NegotiationSession).where(NegotiationSession.id == session_id)
    )
    session = s_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    log_result = await db.execute(
        select(AuditLog).where(AuditLog.session_id == session_id)
        .order_by(AuditLog.timestamp)
    )
    logs = log_result.scalars().all()

    # Pull the persisted receipt (if any) — surfaced at the top level so
    # external verifiers / replay tools don't need to dig into audit_log.
    rcpt_result = await db.execute(
        select(SignedReceipt).where(SignedReceipt.session_id == session_id)
    )
    receipt = rcpt_result.scalar_one_or_none()
    signed_receipt = None
    if receipt is not None:
        signed_receipt = {
            "receipt_id": receipt.receipt_id,
            "policy_id": receipt.policy_id,
            "buyer_agent_id": receipt.buyer_agent_id,
            "merchant_agent_id": receipt.merchant_agent_id,
            "amount_inr": float(receipt.amount_inr),
            "payload_json": receipt.payload_json,
            "signature_b64": base64.b64encode(receipt.agent_signature).decode(),
            "signed_payload_b64": base64.b64encode(receipt.signed_payload).decode(),
            "razorpay_order_id": receipt.razorpay_order_id,
            "razorpay_payment_id": receipt.razorpay_payment_id,
            "created_at": receipt.created_at.isoformat(),
        }

    # Surface flat replay fields at the top level for /replay/:id (3.6) and
    # the replay_negotiation MCP tool. Existing audit_log shape is preserved.
    winner_skill_id = None
    llm_seed = None
    for log in logs:
        if log.event == "auction_winner_selected":
            winner_skill_id = (log.payload or {}).get("winner_skill_id")
            llm_seed = (log.payload or {}).get("llm_seed")
            break

    return {
        "session": {
            "id": session.id, "item": session.item, "status": session.status.value,
            "listed_price": float(session.listed_price),
            "final_price": float(session.final_price) if session.final_price is not None else None,
            "rounds": session.rounds,
            "created_at": session.created_at.isoformat(),
            "settled_at": session.settled_at.isoformat() if session.settled_at else None,
            "policy_id": session.policy_id,
            "buyer_agent_id": session.buyer_agent_id,
            "merchant_agent_id": session.merchant_agent_id,
            "product_id": session.product_id,
        },
        "audit_log": [{"event": l.event, "payload": l.payload,
                       "timestamp": l.timestamp.isoformat()} for l in logs],
        "signed_receipt": signed_receipt,
        "winner_skill_id": winner_skill_id,
        "llm_seed": llm_seed,
        "replay_data": session.replay_data,
    }


@app.post("/commerce/revoke/{session_id}")
async def revoke_session(session_id: str, req: RevokeRequest,
                         db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NegotiationSession).where(NegotiationSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == TxnStatus.SETTLED:
        raise HTTPException(status_code=400, detail="Cannot revoke a settled transaction")

    session.status = TxnStatus.REVOKED
    db.add(AuditLog(
        session_id=session_id,
        agent_id=session.buyer_agent_id, event="session_revoked",
        payload={"owner_id": req.owner_id, "reason": req.reason},
    ))
    await db.commit()
    return {"session_id": session_id, "status": "revoked", "reason": req.reason}


@app.post("/commerce/checkout/{session_id}")
async def checkout_session(
    session_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8),
):
    """Create a Razorpay order for a settled session.

    Idempotent: repeated calls with the same Idempotency-Key return the cached
    order dict. The request_hash is keyed on session_id so two different callers
    with the same key but different session_ids are caught by the mismatch guard."""
    endpoint = "/commerce/checkout"
    # Hash on session_id so the idempotency check is body-independent (no Pydantic body).
    request_hash = hashlib.sha256(session_id.encode()).hexdigest()

    claimed = await _idempotency_claim(db, endpoint, idempotency_key, request_hash)
    if not claimed:
        cached = await _idempotency_replay_or_409(db, endpoint, idempotency_key, request_hash)
        response.headers["Idempotent-Replay"] = "true"
        return cached

    try:
        s_result = await db.execute(
            select(NegotiationSession).where(NegotiationSession.id == session_id)
        )
        session = s_result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.status != TxnStatus.SETTLED:
            raise HTTPException(
                status_code=400,
                detail=f"Session is '{session.status.value}', must be 'settled' to checkout",
            )

        # Fetch the existing SignedReceipt so we can attach the new order ID.
        rcpt_result = await db.execute(
            select(SignedReceipt).where(SignedReceipt.session_id == session_id)
        )
        receipt = rcpt_result.scalar_one_or_none()
        if receipt is None:
            raise HTTPException(status_code=404, detail="No receipt found for session")

        order = create_razorpay_order(
            amount_inr=float(session.final_price),
            item=session.item,
            session_id=session_id,
            agent_id=session.buyer_agent_id,
        )

        # Persist the Razorpay order ID on the receipt so the webhook can correlate.
        receipt.razorpay_order_id = order["id"]
        db.add(receipt)

        db.add(AuditLog(
            session_id=session_id,
            agent_id=session.buyer_agent_id,
            event="razorpay_order_created",
            payload={"razorpay_order_id": order["id"], "amount_paise": order["amount"],
                     "mock": order.get("mock", False)},
        ))

        asyncio.create_task(_ws_publish(session_id, {
            "type": "checkout_created",
            "session_id": session_id,
            "razorpay_order_id": order["id"],
        }))

        body = {
            "session_id": session_id,
            "razorpay_order_id": order["id"],
            "amount_paise": order["amount"],
            "currency": "INR",
            "status": order.get("status", "created"),
            "mock": order.get("mock", False),
        }
        await _idempotency_finalize(db, endpoint, idempotency_key, body)
        await db.commit()
        return body
    except Exception:
        await db.rollback()
        raise


class RazorpayOrderRequest(BaseModel):
    session_id: str
    amount_inr: float


@app.post("/commerce/create-razorpay-order")
async def create_razorpay_order_endpoint(
    req: RazorpayOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a Razorpay test order for any settled session.

    This is a lightweight checkout alternative for the frontend payment step —
    no idempotency required because the call is stateless on our side (we do not
    write to the DB here; the webhook does). Falls back to a fake order ID in
    test/dev when Razorpay credentials are absent."""
    s_result = await db.execute(
        select(NegotiationSession).where(NegotiationSession.id == req.session_id)
    )
    session = s_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    amount_paise = int(req.amount_inr * 100)

    if RAZORPAY_AVAILABLE:
        try:
            import razorpay
            client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
            order = client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "receipt": req.session_id[:40],
                "notes": {"session_id": req.session_id},
            })
            return {
                "order_id": order["id"],
                "amount_paise": amount_paise,
                "key_id": RAZORPAY_KEY_ID,
            }
        except Exception as exc:
            logger.warning("Razorpay order creation failed: %s", exc)

    # Test-mode fallback — deterministic fake order ID so the UI can show the
    # payment step without real Razorpay credentials.
    return {
        "order_id": f"order_TEST_{req.session_id[:16]}",
        "amount_paise": amount_paise,
        "key_id": RAZORPAY_KEY_ID or "rzp_test_demo",
        "test_mode": True,
    }


@app.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive Razorpay payment.captured / payment.failed webhook events.

    Signature verification uses HMAC-SHA256 over the raw request body with
    RAZORPAY_KEY_SECRET as the key, matching Razorpay's webhook spec. When
    RAZORPAY_AVAILABLE is False (mock/dev) the signature check is skipped so
    integration tests can POST without real credentials."""
    raw_body = await request.body()

    if RAZORPAY_AVAILABLE:
        # Razorpay sends the HMAC in X-Razorpay-Signature; reject missing header.
        incoming_sig = request.headers.get("X-Razorpay-Signature", "")
        expected_sig = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_sig, incoming_sig):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Webhook body is not valid JSON")

    event = payload.get("event", "")
    payment_entity = (payload.get("payload") or {}).get("payment", {}).get("entity", {})
    razorpay_order_id = payment_entity.get("order_id")
    razorpay_payment_id = payment_entity.get("id")

    if not razorpay_order_id:
        # Acknowledge non-payment events (e.g. order.paid) without processing.
        return {"status": "ok"}

    rcpt_result = await db.execute(
        select(SignedReceipt).where(SignedReceipt.razorpay_order_id == razorpay_order_id)
    )
    receipt = rcpt_result.scalar_one_or_none()
    if receipt is None:
        # Unknown order — acknowledge so Razorpay stops retrying.
        logger.warning("razorpay_webhook unknown order_id=%s event=%s", razorpay_order_id, event)
        return {"status": "ok"}

    if razorpay_payment_id:
        # Idempotency guard: Razorpay retries the same webhook on network errors.
        # If we've already recorded this exact payment, skip the write.
        if receipt.razorpay_payment_id and receipt.razorpay_payment_id == razorpay_payment_id:
            return {"status": "ok"}  # already processed this payment
        receipt.razorpay_payment_id = razorpay_payment_id
        db.add(receipt)

    db.add(AuditLog(
        session_id=receipt.session_id,
        agent_id=receipt.buyer_agent_id,
        event=f"razorpay_webhook_{event}",
        payload={"razorpay_order_id": razorpay_order_id,
                 "razorpay_payment_id": razorpay_payment_id,
                 "event": event},
    ))

    asyncio.create_task(_ws_publish(receipt.session_id, {
        "type": "payment_event",
        "session_id": receipt.session_id,
        "event": event,
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
    }))

    await db.commit()
    return {"status": "ok"}


@app.websocket("/ws/session/{session_id}")
async def ws_session(session_id: str, websocket: WebSocket):
    """Push real-time session events to connected clients.

    Events are published by save_session_and_audit, checkout_session, and
    razorpay_webhook via _ws_publish. The client receives JSON objects with
    a 'type' discriminator field. Connection is closed cleanly on disconnect
    or when the client sends any message (treated as an unsubscribe signal)."""
    await websocket.accept()
    q = await _ws_subscribe(session_id)
    try:
        while True:
            # Wait for the next event or a client-side close frame.
            # asyncio.wait is used so we can race the queue against the socket.
            queue_task = asyncio.ensure_future(q.get())
            recv_task = asyncio.ensure_future(websocket.receive_text())
            done, pending = await asyncio.wait(
                {queue_task, recv_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()

            if recv_task in done:
                # Any incoming message triggers a clean close.
                break

            if queue_task in done:
                event = queue_task.result()
                await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        _ws_unsubscribe(session_id, q)
