"""
Main FastAPI application — Agentic Commerce Protocol
Endpoints:
  POST /agents/register           — register a new agent
  POST /agents/delegate           — owner signs spending policy
  GET  /agents/{id}/spend         — get agent's daily spend summary
  POST /commerce/negotiate        — run single negotiation session
  POST /commerce/auction          — run multi-merchant auction
  GET  /commerce/sessions         — list all sessions
  GET  /commerce/session/{id}     — session detail + audit log
  POST /commerce/revoke/{id}      — revoke/cancel a session
  GET  /health                    — health check
"""

import uuid
import json
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import init_db, get_db
from models import Agent, SpendingPolicy, NegotiationSession, AuditLog, AgentRole, TxnStatus
from identity import (generate_agent_id, generate_keypair, sign_policy,
                      verify_policy_signature, create_agent_credential, validate_spend)
from negotiation import run_negotiation
from settlement import create_transaction, build_audit_log
from spend_tracker import get_daily_spent, get_spend_summary
from auction import run_auction
from razorpay_settlement import settle_via_razorpay


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="Agentic Commerce Protocol",
    description="A2A negotiation, identity delegation, and payment settlement for AI agents",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterAgentRequest(BaseModel):
    owner_id: str
    role: str = "user_agent"

class DelegateRequest(BaseModel):
    agent_id: str
    owner_private_key: str
    owner_public_key: str
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
    item: str
    listed_price: float
    num_merchants: int = 3
    buyer_priorities: str = "lowest price"
    use_razorpay: bool = True

class RevokeRequest(BaseModel):
    owner_id: str
    reason: str = "Revoked by owner"


async def load_agent_and_credential(agent_id: str, db: AsyncSession):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    pol_result = await db.execute(
        select(SpendingPolicy)
        .where(SpendingPolicy.agent_id == agent_id)
        .order_by(SpendingPolicy.created_at.desc())
    )
    sp = pol_result.scalar_one_or_none()
    if not sp:
        raise HTTPException(status_code=400, detail="No spending policy found for agent")

    policy = {
        "agent_id": sp.agent_id,
        "max_per_txn": sp.max_per_txn,
        "max_per_day": sp.max_per_day,
        "currency": sp.currency,
        "allow_auto_renew": sp.allow_auto_renew,
        "categories": sp.categories
    }
    credential = create_agent_credential(agent_id, agent.owner_id, policy, sp.signature)
    return agent, sp, credential


async def save_session_and_audit(session: dict, credential: dict,
                                  agent_private_key: str, db: AsyncSession,
                                  use_razorpay: bool = False):
    merchant_id = f"did:agent:merchant_{uuid.uuid4().hex[:8]}"

    ns = NegotiationSession(
        id=session["session_id"],
        buyer_agent_id=credential["agent_id"],
        merchant_agent_id=merchant_id,
        item=session["item"],
        initial_price=session["listed_price"],
        final_price=session.get("final_price"),
        rounds=json.dumps(session.get("rounds", [])),
        status=TxnStatus(session["status"]),
        settled_at=datetime.utcnow() if session["status"] == "settled" else None
    )
    db.add(ns)
    await db.flush()

    transaction = True
    razorpay_receipt = True

    if session["status"] == "settled":
        transaction = create_transaction(session, credential, agent_private_key)
        if use_razorpay:
            razorpay_receipt = settle_via_razorpay(session, credential)

    logs = build_audit_log(session, transaction)
    for entry in logs:
        al = AuditLog(
            id=entry["log_id"],
            session_id=session["session_id"],
            agent_id=credential["agent_id"],
            event=entry["event"],
            payload=json.dumps(entry["payload"])
        )
        db.add(al)

    await db.commit()
    return transaction, razorpay_receipt, logs


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agentic-commerce-protocol", "version": "1.0.0"}


@app.post("/agents/register")
async def register_agent(req: RegisterAgentRequest, db: AsyncSession = Depends(get_db)):
    agent_id = generate_agent_id()
    private_pem, public_pem = generate_keypair()
    agent = Agent(
        id=agent_id, role=AgentRole(req.role),
        public_key=public_pem, owner_id=req.owner_id
    )
    db.add(agent)
    await db.commit()
    return {
        "agent_id": agent_id, "public_key": public_pem,
        "private_key": private_pem, "role": req.role,
        "message": "Agent registered. Store private_key securely — not saved on server."
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
        "allow_auto_renew": req.allow_auto_renew, "categories": req.categories
    }

    private_key_clean = req.owner_private_key.replace("\\n", "\n").strip()
    public_key_clean = req.owner_public_key.replace("\\n", "\n").strip()

    signature = sign_policy(private_key_clean, policy)
    if not verify_policy_signature(public_key_clean, policy, signature):
        raise HTTPException(status_code=400, detail="Policy signature verification failed")

    sp = SpendingPolicy(
        id=f"pol_{uuid.uuid4().hex[:12]}", agent_id=req.agent_id,
        max_per_txn=req.max_per_txn, max_per_day=req.max_per_day,
        currency=req.currency, allow_auto_renew=req.allow_auto_renew,
        categories=req.categories, signature=signature
    )
    db.add(sp)
    await db.commit()

    credential = create_agent_credential(req.agent_id, agent.owner_id, policy, signature)
    return {"policy_id": sp.id, "credential": credential,
            "message": "Policy signed and stored. Agent is ready to transact."}


@app.get("/agents/{agent_id}/spend")
async def get_agent_spend(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent not found")
    return await get_spend_summary(agent_id, db)


@app.post("/commerce/negotiate")
async def negotiate(req: NegotiateRequest, db: AsyncSession = Depends(get_db)):
    agent, sp, credential = await load_agent_and_credential(req.buyer_agent_id, db)
    daily_spent = await get_daily_spent(req.buyer_agent_id, db)

    allowed, reason = validate_spend(credential, req.initial_offer, daily_spent)
    if not allowed:
        raise HTTPException(status_code=400, detail=f"Policy check failed: {reason}")

    session = run_negotiation(
        item=req.item, listed_price=req.listed_price,
        initial_offer=req.initial_offer, credential=credential,
        daily_spent=daily_spent
    )

    transaction, razorpay_receipt, logs = await save_session_and_audit(
        session, credential, req.agent_private_key, db, req.use_razorpay
    )

    return {
        "session_id": session["session_id"],
        "status": session["status"],
        "item": req.item,
        "listed_price": req.listed_price,
        "final_price": session.get("final_price"),
        "rounds_count": len(session.get("rounds", [])),
        "transaction": transaction,
        "razorpay_receipt": razorpay_receipt,
        "audit_entries": len(logs),
        "daily_spent_after": daily_spent + (session.get("final_price") or 0)
    }


@app.post("/commerce/auction")
async def auction(req: AuctionRequest, db: AsyncSession = Depends(get_db)):
    """Multi-merchant auction — multiple merchants compete, buyer picks best price."""
    agent, sp, credential = await load_agent_and_credential(req.buyer_agent_id, db)
    daily_spent = await get_daily_spent(req.buyer_agent_id, db)

    allowed, reason = validate_spend(credential, 1.0, daily_spent)
    if not allowed:
        raise HTTPException(status_code=400, detail=f"Daily limit reached: {reason}")

    result = run_auction(
        item=req.item, listed_price=req.listed_price,
        credential=credential, num_merchants=req.num_merchants,
        buyer_priorities=req.buyer_priorities
    )

    if result["status"] == "settled":
        session_dict = {
            "session_id": result["auction_id"],
            "item": req.item,
            "listed_price": req.listed_price,
            "initial_offer": result["final_price"],
            "final_price": result["final_price"],
            "rounds": [{"round": 1, "type": "auction",
                        "quotes": result["all_quotes"],
                        "winner": result["winner"],
                        "timestamp": result["created_at"]}],
            "status": "settled",
            "buyer_agent_id": req.buyer_agent_id
        }
        transaction, razorpay_receipt, logs = await save_session_and_audit(
            session_dict, credential, req.agent_private_key, db, req.use_razorpay
        )
        result["transaction"] = transaction
        result["razorpay_receipt"] = razorpay_receipt
        result["audit_entries"] = len(logs)

    return result


@app.get("/commerce/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NegotiationSession).order_by(NegotiationSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [{"session_id": s.id, "item": s.item, "status": s.status,
            "initial_price": s.initial_price, "final_price": s.final_price,
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

    return {
        "session": {
            "id": session.id, "item": session.item, "status": session.status,
            "initial_price": session.initial_price, "final_price": session.final_price,
            "rounds": json.loads(session.rounds),
            "created_at": session.created_at.isoformat(),
            "settled_at": session.settled_at.isoformat() if session.settled_at else None
        },
        "audit_log": [{"event": l.event, "payload": json.loads(l.payload),
                       "timestamp": l.timestamp.isoformat()} for l in logs]
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
        id=f"log_{uuid.uuid4().hex[:8]}", session_id=session_id,
        agent_id=session.buyer_agent_id, event="session_revoked",
        payload=json.dumps({"owner_id": req.owner_id, "reason": req.reason})
    ))
    await db.commit()
    return {"session_id": session_id, "status": "revoked", "reason": req.reason}
