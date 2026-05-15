"""Merchant dashboard routes (ADR-012).

Prefix: /merchant
Auth: Bearer JWT — all routes require is_merchant=True.

NOTE: audit_log.session_id is NOT NULL FK to negotiation_sessions — product
CRUD has no session to reference, so mutations are logged via Python logger
rather than the audit_log table (which is session-scoped by design).
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import UserPayload, get_current_user
from database import get_db
from models import Agent, AgentSkill, Merchant, MerchantAgent, NegotiationSession, Product

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/merchant", tags=["merchant"])


# ── Pydantic models ──────────────────────────────────────────────────────────

class MerchantProductCreate(BaseModel):
    title: str
    description: str
    category: str  # groceries|electronics|clothing|home|food|other
    floor_price_inr: float
    listed_price_inr: float
    delivery_radius_km: float | None = None
    delivery_days_min: int | None = None
    delivery_days_max: int | None = None
    image_url: str | None = None


class MerchantProductUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    floor_price_inr: float | None = None
    listed_price_inr: float | None = None
    delivery_radius_km: float | None = None
    delivery_days_min: int | None = None
    delivery_days_max: int | None = None
    image_url: str | None = None


class DeliveryUpdateRequest(BaseModel):
    delivery_status: str
    proof_image_url: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _product_dict(p: Product) -> dict[str, Any]:
    """Serialize a Product ORM row to a plain dict for JSON responses."""
    return {
        "id": p.id,
        "title": p.name,          # DB column is 'name'; API surface uses 'title'
        "description": p.description,
        "category": p.category,
        "floor_price_inr": float(p.floor_price),
        "listed_price_inr": float(p.listed_price),
        "delivery_radius_km": None,   # not yet a DB column — returned as None
        "delivery_days_min": None,
        "delivery_days_max": None,
        "image_url": p.image_url,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat(),
    }


async def _require_merchant(
    current_user: UserPayload,
    db: AsyncSession,
) -> Merchant | None:
    """Return the Merchant row for this user, or None if none exists yet."""
    result = await db.execute(
        select(Merchant).where(Merchant.owner_user_id == current_user.user_id)
    )
    return result.scalar_one_or_none()


async def _get_merchant_product(
    product_id: str,
    merchant: Merchant,
    db: AsyncSession,
) -> Product:
    """Fetch a product and verify it belongs to this merchant."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.merchant_id == merchant.id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/products")
async def list_merchant_products(
    current_user: UserPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    if not current_user.is_merchant:
        raise HTTPException(status_code=403, detail="Merchant access required")

    merchant = await _require_merchant(current_user, db)
    if not merchant:
        return []

    result = await db.execute(
        select(Product).where(Product.merchant_id == merchant.id)
    )
    products = result.scalars().all()
    return [_product_dict(p) for p in products]


@router.post("/products", status_code=201)
async def create_merchant_product(
    body: MerchantProductCreate,
    current_user: UserPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not current_user.is_merchant:
        raise HTTPException(status_code=403, detail="Merchant access required")

    # Find or create the Merchant row for this user.
    merchant = await _require_merchant(current_user, db)
    if not merchant:
        merchant = Merchant(
            id=f"merch_{current_user.user_id[:8]}",
            name=current_user.email,   # User has no display_name column
            address="-",
            city="Mumbai",
            pincode="400001",
            lat=19.076,
            lng=72.877,
            owner_user_id=current_user.user_id,
        )
        db.add(merchant)
        await db.flush()  # get PK into DB before referencing it below

    product_id = f"prod_{merchant.id}_{uuid.uuid4().hex[:6]}"
    product = Product(
        id=product_id,
        merchant_id=merchant.id,
        name=body.title,
        description=body.description,
        category=body.category,
        floor_price=body.floor_price_inr,
        listed_price=body.listed_price_inr,
        image_url=body.image_url,
    )
    db.add(product)
    await db.flush()

    # Pick first available skill for the MerchantAgent.
    skill_result = await db.execute(select(AgentSkill).limit(1))
    skill = skill_result.scalar_one_or_none()
    if skill:
        ma = MerchantAgent(
            id=f"ma_{product.id}",
            merchant_id=merchant.id,
            # 32 zero bytes satisfy the Ed25519 length CHECK; real key issued post-MVP
            public_key=b"\x00" * 32,
            skill_id=skill.id,
        )
        db.add(ma)

    await db.commit()
    logger.info(
        "product_created user_id=%s product_id=%s",
        current_user.user_id, product_id,
    )
    return _product_dict(product)


@router.patch("/products/{product_id}")
async def update_merchant_product(
    product_id: str,
    body: MerchantProductUpdate,
    current_user: UserPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not current_user.is_merchant:
        raise HTTPException(status_code=403, detail="Merchant access required")

    merchant = await _require_merchant(current_user, db)
    if not merchant:
        raise HTTPException(status_code=404, detail="No merchant profile found")

    product = await _get_merchant_product(product_id, merchant, db)

    # Only update fields that were explicitly provided.
    update_data = body.model_dump(exclude_none=True)
    field_map = {
        "title": "name",
        "floor_price_inr": "floor_price",
        "listed_price_inr": "listed_price",
    }
    for api_field, value in update_data.items():
        db_field = field_map.get(api_field, api_field)
        # Skip fields that don't exist as DB columns (e.g. delivery_radius_km).
        if hasattr(product, db_field):
            setattr(product, db_field, value)

    db.add(product)
    await db.commit()
    logger.info(
        "product_updated user_id=%s product_id=%s fields=%s",
        current_user.user_id, product_id, list(update_data.keys()),
    )
    return _product_dict(product)


@router.delete("/products/{product_id}", status_code=200)
async def delete_merchant_product(
    product_id: str,
    current_user: UserPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not current_user.is_merchant:
        raise HTTPException(status_code=403, detail="Merchant access required")

    merchant = await _require_merchant(current_user, db)
    if not merchant:
        raise HTTPException(status_code=404, detail="No merchant profile found")

    product = await _get_merchant_product(product_id, merchant, db)
    product.is_active = False
    db.add(product)
    await db.commit()
    logger.info(
        "product_deleted user_id=%s product_id=%s",
        current_user.user_id, product_id,
    )
    return {"ok": True, "product_id": product_id}


@router.get("/deals")
async def list_merchant_deals(
    current_user: UserPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return sessions won by this merchant's agents."""
    if not current_user.is_merchant:
        raise HTTPException(status_code=403, detail="Merchant access required")

    merchant = await _require_merchant(current_user, db)
    if not merchant:
        return []

    # Collect all merchant_agent IDs for this merchant.
    ma_result = await db.execute(
        select(MerchantAgent).where(MerchantAgent.merchant_id == merchant.id)
    )
    merchant_agent_ids = {ma.id for ma in ma_result.scalars().all()}
    if not merchant_agent_ids:
        return []

    # Sessions where the winning merchant_agent belongs to this user.
    sessions_result = await db.execute(
        select(NegotiationSession).where(
            NegotiationSession.merchant_agent_id.in_(merchant_agent_ids)
        ).order_by(NegotiationSession.created_at.desc())
    )
    sessions = sessions_result.scalars().all()

    # Batch-fetch products for titles.
    product_ids = {s.product_id for s in sessions}
    product_map: dict[str, str] = {}
    if product_ids:
        prod_result = await db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        for p in prod_result.scalars().all():
            product_map[p.id] = p.name

    return [
        {
            "id": s.id,
            "status": s.status.value,
            "final_price": float(s.final_price) if s.final_price is not None else None,
            "created_at": s.created_at.isoformat(),
            "product_title": product_map.get(s.product_id),
            "buyer_agent_id": s.buyer_agent_id,
        }
        for s in sessions
    ]


@router.put("/delivery/{session_id}")
async def update_delivery(
    session_id: str,
    body: DeliveryUpdateRequest,
    current_user: UserPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not current_user.is_merchant:
        raise HTTPException(status_code=403, detail="Merchant access required")

    valid_statuses = {"dispatched", "delivered"}
    if body.delivery_status not in valid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"delivery_status must be one of {valid_statuses}",
        )

    merchant = await _require_merchant(current_user, db)
    if not merchant:
        raise HTTPException(status_code=404, detail="No merchant profile found")

    # Verify this session was won by one of this merchant's agents.
    ma_result = await db.execute(
        select(MerchantAgent).where(MerchantAgent.merchant_id == merchant.id)
    )
    merchant_agent_ids = {ma.id for ma in ma_result.scalars().all()}

    session_result = await db.execute(
        select(NegotiationSession).where(NegotiationSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    if not session or session.merchant_agent_id not in merchant_agent_ids:
        raise HTTPException(status_code=404, detail="Session not found")

    # delivery_status and delivery_proof_url are not yet DB columns — store in
    # rounds JSON as a delivery event (avoids a migration for the MVP).
    rounds = list(session.rounds or [])
    rounds.append({
        "type": "delivery_update",
        "delivery_status": body.delivery_status,
        "proof_image_url": body.proof_image_url,
    })
    session.rounds = rounds
    db.add(session)
    await db.commit()

    logger.info(
        "delivery_updated user_id=%s session_id=%s status=%s",
        current_user.user_id, session_id, body.delivery_status,
    )
    return {"ok": True, "session_id": session_id, "delivery_status": body.delivery_status}


@router.get("/stats")
async def merchant_stats(
    current_user: UserPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not current_user.is_merchant:
        raise HTTPException(status_code=403, detail="Merchant access required")

    merchant = await _require_merchant(current_user, db)
    if not merchant:
        return {
            "active_listings": 0,
            "pending_deliveries": 0,
            "total_deals": 0,
            "total_revenue_inr": 0.0,
        }

    # Active listings count.
    prod_result = await db.execute(
        select(Product).where(
            Product.merchant_id == merchant.id,
            Product.is_active == True,  # noqa: E712
        )
    )
    active_listings = len(prod_result.scalars().all())

    # All sessions for this merchant.
    ma_result = await db.execute(
        select(MerchantAgent).where(MerchantAgent.merchant_id == merchant.id)
    )
    merchant_agent_ids = {ma.id for ma in ma_result.scalars().all()}

    total_deals = 0
    total_revenue = 0.0
    if merchant_agent_ids:
        sessions_result = await db.execute(
            select(NegotiationSession).where(
                NegotiationSession.merchant_agent_id.in_(merchant_agent_ids)
            )
        )
        sessions = sessions_result.scalars().all()
        total_deals = len(sessions)
        total_revenue = sum(
            float(s.final_price)
            for s in sessions
            if s.final_price is not None
        )

    return {
        "active_listings": active_listings,
        "pending_deliveries": 0,   # no delivery_status column yet — placeholder
        "total_deals": total_deals,
        "total_revenue_inr": round(total_revenue, 2),
    }
