"""Buyer dashboard routes (ADR-012).

Prefix: /buyer
Auth: Bearer JWT — all routes require is_buyer=True.

NOTE: audit_log.session_id is NOT NULL FK to negotiation_sessions. The dispute
route writes a delivery_update event into session.rounds (same pattern as
merchant delivery) because we cannot write an audit_log row without a real
session, and disputes ARE tied to sessions — so we write audit_log here.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import UserPayload, get_current_user
from database import get_db
from models import Agent, AuditLog, NegotiationSession, TxnStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/buyer", tags=["buyer"])


# ── Pydantic models ──────────────────────────────────────────────────────────

class DisputeRequest(BaseModel):
    reason: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _session_dict(s: NegotiationSession) -> dict[str, Any]:
    """Serialize a NegotiationSession to the buyer list-view shape."""
    return {
        "id": s.id,
        "status": s.status.value,
        "payment_status": None,       # no separate payment_status column yet
        "delivery_status": None,      # stored in rounds; not a dedicated column
        "final_price": float(s.final_price) if s.final_price is not None else None,
        "platform_fee_amount": None,  # stored on SignedReceipt; not joined here
        "created_at": s.created_at.isoformat(),
        "product_id": s.product_id,
    }


async def _buyer_agent_ids(current_user: UserPayload, db: AsyncSession) -> set[str]:
    """Return all agent IDs owned by this user."""
    result = await db.execute(
        select(Agent).where(Agent.owner_user_id == current_user.user_id)
    )
    return {a.id for a in result.scalars().all()}


async def _get_buyer_session(
    session_id: str,
    agent_ids: set[str],
    db: AsyncSession,
) -> NegotiationSession:
    """Fetch session and verify it belongs to one of the buyer's agents."""
    result = await db.execute(
        select(NegotiationSession).where(NegotiationSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session or session.buyer_agent_id not in agent_ids:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/deals")
async def list_buyer_deals(
    status: str | None = None,
    current_user: UserPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    if not current_user.is_buyer:
        raise HTTPException(status_code=403, detail="Buyer access required")

    agent_ids = await _buyer_agent_ids(current_user, db)
    if not agent_ids:
        return []

    stmt = select(NegotiationSession).where(
        NegotiationSession.buyer_agent_id.in_(agent_ids)
    ).order_by(NegotiationSession.created_at.desc())

    if status is not None:
        # Validate the status value matches a known TxnStatus to avoid a DB error.
        try:
            stmt = stmt.where(NegotiationSession.status == TxnStatus(status))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Unknown status: {status}")

    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return [_session_dict(s) for s in sessions]


@router.get("/deal/{session_id}")
async def get_buyer_deal(
    session_id: str,
    current_user: UserPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not current_user.is_buyer:
        raise HTTPException(status_code=403, detail="Buyer access required")

    agent_ids = await _buyer_agent_ids(current_user, db)
    session = await _get_buyer_session(session_id, agent_ids, db)

    log_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.session_id == session_id)
        .order_by(AuditLog.timestamp)
    )
    logs = log_result.scalars().all()

    return {
        "session": {
            "id": session.id,
            "item": session.item,
            "status": session.status.value,
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
        "audit_log": [
            {
                "event": l.event,
                "payload": l.payload,
                "timestamp": l.timestamp.isoformat(),
            }
            for l in logs
        ],
    }


@router.post("/dispute/{session_id}")
async def open_dispute(
    session_id: str,
    body: DisputeRequest = DisputeRequest(),
    current_user: UserPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not current_user.is_buyer:
        raise HTTPException(status_code=403, detail="Buyer access required")

    agent_ids = await _buyer_agent_ids(current_user, db)
    session = await _get_buyer_session(session_id, agent_ids, db)

    # Record dispute as a delivery event in rounds (delivery_status not a DB column yet).
    rounds = list(session.rounds or [])
    rounds.append({
        "type": "delivery_update",
        "delivery_status": "disputed",
        "reason": body.reason,
    })
    session.rounds = rounds
    db.add(session)

    # audit_log requires session_id FK — we have it here, so we can write it.
    db.add(AuditLog(
        session_id=session_id,
        agent_id=session.buyer_agent_id,
        event="dispute_opened",
        payload={"user_id": current_user.user_id, "reason": body.reason},
    ))

    await db.commit()
    logger.info("dispute_opened user_id=%s session_id=%s", current_user.user_id, session_id)
    return {"ok": True, "session_id": session_id}


@router.get("/stats")
async def buyer_stats(
    current_user: UserPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not current_user.is_buyer:
        raise HTTPException(status_code=403, detail="Buyer access required")

    agent_ids = await _buyer_agent_ids(current_user, db)
    active_agents = len(agent_ids)

    if not agent_ids:
        return {"total_deals": 0, "total_saved_inr": 0.0, "active_agents": 0}

    result = await db.execute(
        select(NegotiationSession).where(
            NegotiationSession.buyer_agent_id.in_(agent_ids)
        )
    )
    sessions = result.scalars().all()
    total_deals = len(sessions)

    # total_saved_inr: NegotiationSession has no max_price column; return 0.
    total_saved = 0.0

    return {
        "total_deals": total_deals,
        "total_saved_inr": round(total_saved, 2),
        "active_agents": active_agents,
    }
