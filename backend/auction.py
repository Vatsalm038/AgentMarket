"""
Module: Multi-Merchant Auction (ADR-011)

Competitors are shortlisted from the seeded products/merchants/merchant_agents
tables rather than hard-coded fixtures. The auction is keyed off an anchor
`product_id` resolved upstream (matcher in 2.1, hand-picked for now).

Layering: the auction reads from the DB but does not commit — the caller owns
the transaction so audit_log + negotiation_sessions + signed_receipts land
atomically with the auction's outcome.

LLM determinism: every OpenAI call sets temperature=0 and passes a stable
per-(auction, merchant) seed so verifiable-replay (ADR-007) can re-run a
historical auction and obtain byte-identical quotes (modulo OpenAI's seed
guarantees).
"""

import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from identity import validate_spend
from models import AgentSkill, Merchant, MerchantAgent, Product


logger = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
_LLM_MODEL = "gpt-4o-mini"


# ── Pure helpers (clamps + deterministic seed) ──────────────────────────────

def _clamp_quote(raw_quote: float, floor_price: float, listed_price: float,
                 buyer_budget: float) -> float:
    """Clamp a merchant's proposed quote into the band
    [floor_price, min(listed_price, buyer_budget)].

    Pure function so it's trivially unit-testable without LLM/DB. The LLM is
    never trusted to do this arithmetic itself (CLAUDE.md rule 4)."""
    upper = min(float(listed_price), float(buyer_budget))
    lower = float(floor_price)
    if upper < lower:
        # Buyer budget can't even meet the merchant's floor — clamp to floor and
        # let the outer auction reject the quote against policy_max.
        upper = lower
    quote = float(raw_quote)
    quote = max(lower, min(quote, upper))
    return round(quote, 2)


def _stable_seed(auction_id: str, *parts: str) -> int:
    """Derive a stable positive int63 seed from auction_id + extra parts. Used
    as OpenAI `seed` so re-running an auction with the same inputs yields the
    same generation (ADR-007 verifiable replay)."""
    h = hashlib.sha256("|".join((auction_id, *parts)).encode()).digest()
    # Take 8 bytes and mask the sign bit so the value fits in a signed int64
    # (BigInteger column for replay_seed) and survives JSON round-trips.
    return int.from_bytes(h[:8], "big") & ((1 << 63) - 1)


# ── DB shortlist ────────────────────────────────────────────────────────────

async def _shortlist_competitors(
    db: AsyncSession, anchor_product_id: str, policy_max: float,
    num_merchants: int,
) -> list[dict]:
    """Return up to `num_merchants` competitor rows for the anchor product's
    category, ordered by floor_price ASC, *including* the anchor itself.

    Each row dict carries everything the LLM call + clamp need:
      product_id, listed_price, floor_price, category,
      merchant_id, merchant_name,
      merchant_agent_id, skill_id, system_prompt_template, skill_name.

    Caller's transaction is reused — no commit here.
    """
    anchor_res = await db.execute(select(Product).where(Product.id == anchor_product_id))
    anchor = anchor_res.scalar_one_or_none()
    if anchor is None:
        return []

    cap = max(2, min(int(num_merchants), 6))

    # Shortlist by category + active + within buyer's per-txn cap, cheapest first.
    # The anchor row itself satisfies the same predicate, so it's naturally included.
    # NOTE: neither MerchantAgent nor AgentSkill has an is_active column in the
    # current schema (migration 365bcb27952f); if added later, filter here.
    stmt = (
        select(Product, Merchant, MerchantAgent, AgentSkill)
        .join(Merchant, Merchant.id == Product.merchant_id)
        .join(MerchantAgent, MerchantAgent.merchant_id == Merchant.id)
        .join(AgentSkill, AgentSkill.id == MerchantAgent.skill_id)
        .where(
            Product.category == anchor.category,
            Product.is_active.is_(True),
            Product.listed_price <= Decimal(str(policy_max)),
        )
        .order_by(Product.floor_price.asc())
        .limit(cap)
    )
    rows = (await db.execute(stmt)).all()

    # Invariant on the returned list: the anchor row (when within budget) sits at
    # index 0. Competitors follow in floor_price ASC order. The anchor position is
    # load-bearing for the buyer-eval prompt which frames "you asked about X".
    shortlist: list[dict] = []
    seen_merchant_agents: set[str] = set()
    for product, merchant, magent, skill in rows:
        # Defend against the duplicate-join risk flagged in ADR-011 follow-up:
        # if a merchant ever has >1 merchant_agent, the same merchant could
        # appear twice. Keep the first occurrence only.
        if magent.id in seen_merchant_agents:
            continue
        seen_merchant_agents.add(magent.id)
        shortlist.append({
            "product_id": product.id,
            "listed_price": float(product.listed_price),
            "floor_price": float(product.floor_price),
            "category": product.category,
            "product_name": product.name,
            "merchant_id": merchant.id,
            "merchant_name": merchant.name,
            "merchant_agent_id": magent.id,
            "skill_id": skill.id,
            "skill_name": skill.name,
            "system_prompt_template": skill.system_prompt_template,
        })

    # Guarantee the anchor row appears even if it wasn't in the top-N by floor.
    if not any(r["product_id"] == anchor.id for r in shortlist):
        # Pull the anchor's full join row separately and prepend it; drop the
        # last entry to respect the cap.
        anchor_stmt = (
            select(Product, Merchant, MerchantAgent, AgentSkill)
            .join(Merchant, Merchant.id == Product.merchant_id)
            .join(MerchantAgent, MerchantAgent.merchant_id == Merchant.id)
            .join(AgentSkill, AgentSkill.id == MerchantAgent.skill_id)
            .where(Product.id == anchor.id)
            .limit(1)
        )
        anchor_row = (await db.execute(anchor_stmt)).first()
        if anchor_row is not None:
            product, merchant, magent, skill = anchor_row
            shortlist.insert(0, {
                "product_id": product.id,
                "listed_price": float(product.listed_price),
                "floor_price": float(product.floor_price),
                "category": product.category,
                "product_name": product.name,
                "merchant_id": merchant.id,
                "merchant_name": merchant.name,
                "merchant_agent_id": magent.id,
                "skill_id": skill.id,
                "skill_name": skill.name,
                "system_prompt_template": skill.system_prompt_template,
            })
            shortlist = shortlist[:cap]

    return shortlist


# ── LLM calls (temperature=0 + deterministic seed) ──────────────────────────

async def _merchant_initial_quote(
    auction_id: str, item: str, buyer_budget: float, competitor: dict,
) -> dict:
    """Ask one merchant agent for an opening auction quote. The LLM proposes a
    number; Python clamps it into [floor_price, min(listed_price, buyer_budget)].
    """
    floor = competitor["floor_price"]
    listed = competitor["listed_price"]
    upper = min(listed, buyer_budget)
    # Floor can exceed buyer budget — caller will filter by policy_max afterwards.

    prompt = (
        f"You are merchant agent '{competitor['merchant_name']}' (skill: "
        f"{competitor['skill_name']}) competing in an auction for the buyer's "
        f"order: '{item}'.\n"
        f"Your product: {competitor['product_name']}.\n"
        f"Listed price: INR {listed}. Your floor: INR {floor}. "
        f"Buyer budget: INR {buyer_budget}.\n"
        f"Other merchants are competing — bid competitively to win.\n"
        f"Your quote MUST be between INR {floor} and INR {upper:.2f}; outside "
        f"the band will be clamped.\n"
        "\n"
        "Respond ONLY with one line of valid JSON, no markdown:\n"
        '{"quote": <number>, "pitch": "<one sentence why buyer should choose you>"}'
    )

    seed = _stable_seed(auction_id, competitor["merchant_agent_id"], "quote")
    response = await _client.chat.completions.create(
        model=_LLM_MODEL,
        max_tokens=200,
        temperature=0,
        seed=seed,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Fall back to the floor — the LLM gave us garbage; the clamp would
        # have rejected it anyway. Pitch is empty so the UI can show the issue.
        parsed = {"quote": floor, "pitch": "(unparseable response)"}

    clamped = _clamp_quote(parsed.get("quote", floor), floor, listed, buyer_budget)
    return {
        "merchant_id": competitor["merchant_id"],
        "merchant_name": competitor["merchant_name"],
        "merchant_agent_id": competitor["merchant_agent_id"],
        "product_id": competitor["product_id"],
        "product_name": competitor["product_name"],
        "skill_id": competitor["skill_id"],
        "floor_price": floor,
        "listed_price": listed,
        "quote": clamped,
        "pitch": str(parsed.get("pitch", ""))[:280],
        "llm_seed": seed,
    }


async def _buyer_evaluate_quotes(
    auction_id: str, item: str, valid_quotes: list[dict],
    policy_max: float, buyer_priorities: str,
) -> dict:
    """Buyer agent picks a winner. Result is clamped + reconciled to the
    cheapest valid quote if the LLM names a merchant outside the valid set."""
    quotes_text = "\n".join(
        f"- {q['merchant_name']} (product {q['product_name']}): INR {q['quote']} — {q['pitch']}"
        for q in valid_quotes
    )

    prompt = (
        f"You are a buyer agent selecting the best deal for '{item}'.\n"
        f"Policy max per transaction: INR {policy_max}. Priorities: {buyer_priorities}.\n"
        "\n"
        f"Valid quotes:\n{quotes_text}\n"
        "\n"
        "Pick the best option based on price and pitch quality.\n"
        "Respond ONLY with one line of valid JSON, no markdown:\n"
        '{"winner_merchant_name": "<exact name from list>", "reason": "<why, <=20 words>"}'
    )

    seed = _stable_seed(auction_id, "buyer_eval")
    response = await _client.chat.completions.create(
        model=_LLM_MODEL,
        max_tokens=300,
        temperature=0,
        seed=seed,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"winner_merchant_name": None, "reason": "(unparseable response)"}

    # Reconcile the LLM's named winner to an actual quote row. If it picked
    # something not in the valid set, fall back to the cheapest valid quote —
    # never let the LLM invent a merchant.
    winner_quote = next(
        (q for q in valid_quotes if q["merchant_name"] == parsed.get("winner_merchant_name")),
        None,
    )
    if winner_quote is None:
        winner_quote = min(valid_quotes, key=lambda q: q["quote"])

    final_price = min(float(winner_quote["quote"]), float(policy_max))
    return {
        "winner_merchant_id": winner_quote["merchant_id"],
        "winner_merchant_name": winner_quote["merchant_name"],
        "winner_merchant_agent_id": winner_quote["merchant_agent_id"],
        "winner_product_id": winner_quote["product_id"],
        "winner_skill_id": winner_quote["skill_id"],
        "reason": str(parsed.get("reason", ""))[:280],
        "final_price": round(final_price, 2),
        "llm_seed": seed,
    }


# ── Public entry point ──────────────────────────────────────────────────────

async def run_auction(
    db: AsyncSession,
    anchor_product_id: str,
    credential: dict,
    buyer_priorities: str = "lowest price",
    num_merchants: int = 3,
) -> dict:
    """Run a multi-merchant auction anchored on `anchor_product_id`.

    The caller (FastAPI endpoint) owns the transaction; this function only
    reads. It returns a dict shaped like the legacy run_auction result so the
    save-session path can ingest it unchanged, plus a `winner_merchant_agent_id`
    / `winner_product_id` so persistence can write the correct FKs.
    """
    auction_id = f"auction_{uuid.uuid4().hex[:12]}"
    policy_max = float(credential["policy"]["max_per_txn"])
    buyer_agent_id = credential["agent_id"]

    shortlist = await _shortlist_competitors(db, anchor_product_id, policy_max, num_merchants)
    if not shortlist:
        return {
            "session_id": auction_id, "status": "failed",
            "reason": f"No active competitors for product {anchor_product_id}",
            "all_quotes": [], "winner": None,
            "buyer_agent_id": buyer_agent_id,
            "winner_merchant_agent_id": None,
            "winner_product_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    # Use the anchor's product name as the canonical item description so the
    # LLM prompts and the persisted session.item agree.
    anchor_row = next(
        (r for r in shortlist if r["product_id"] == anchor_product_id),
        shortlist[0],
    )
    item = anchor_row["product_name"]
    listed_price = anchor_row["listed_price"]

    # Anchor unaffordability check: if even the anchor's floor exceeds the buyer's
    # per-txn cap, no clamp can rescue it — fail fast before burning an LLM call.
    # (Anchor's listed_price > policy_max is still negotiable as long as the floor
    # fits, since the clamp uses min(listed, policy_max) as the upper bound.)
    if anchor_row["floor_price"] > policy_max:
        return {
            "session_id": auction_id, "status": "failed",
            "reason": "anchor_unaffordable",
            "anchor_product_id": anchor_row["product_id"],
            "anchor_floor_price": anchor_row["floor_price"],
            "policy_max": policy_max,
            "all_quotes": [], "winner": None,
            "buyer_agent_id": buyer_agent_id,
            "winner_merchant_agent_id": None,
            "winner_product_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    logger.info(
        "auction_start auction_id=%s item=%s anchor_listed=%s budget=%s merchants=%d",
        auction_id, item, listed_price, policy_max, len(shortlist),
    )

    # Phase 1: collect quotes concurrently. Each call has a deterministic seed
    # derived from (auction_id, merchant_agent_id), so concurrency is safe for
    # replay. Per-merchant failures are isolated via return_exceptions=True.
    results = await asyncio.gather(
        *[_merchant_initial_quote(auction_id, item, policy_max, c) for c in shortlist],
        return_exceptions=True,
    )
    quotes: list[dict] = []
    for competitor, res in zip(shortlist, results):
        if isinstance(res, Exception):
            logger.exception(
                "merchant_quote_failed auction_id=%s merchant=%s",
                auction_id, competitor["merchant_name"],
            )
            continue
        quotes.append(res)
        logger.info(
            "merchant_quote auction_id=%s merchant=%s quote=%.2f",
            auction_id, res["merchant_name"], res["quote"],
        )

    if not quotes:
        return {
            "session_id": auction_id, "status": "failed",
            "reason": "No merchants responded",
            "all_quotes": [], "winner": None,
            "buyer_agent_id": buyer_agent_id,
            "winner_merchant_agent_id": None,
            "winner_product_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    # Defence-in-depth: _clamp_quote already pins each quote to <= min(listed,
    # buyer_budget), so this filter should be a no-op. Kept because CLAUDE.md
    # rule 4 says we never trust LLM math — a buggy clamp upstream must not let
    # an over-budget quote reach the buyer-eval prompt.
    valid_quotes = [q for q in quotes if q["quote"] <= policy_max]
    if not valid_quotes:
        return {
            "session_id": auction_id, "status": "failed",
            "reason": f"All quotes exceeded policy max INR {policy_max}",
            "all_quotes": quotes, "valid_quotes_count": 0, "winner": None,
            "buyer_agent_id": buyer_agent_id,
            "winner_merchant_agent_id": None,
            "winner_product_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    logger.info(
        "auction_phase2 auction_id=%s valid_quotes=%d",
        auction_id, len(valid_quotes),
    )
    winner = await _buyer_evaluate_quotes(
        auction_id, item, valid_quotes, policy_max, buyer_priorities
    )
    logger.info(
        "auction_winner auction_id=%s merchant=%s final_price=%.2f",
        auction_id, winner["winner_merchant_name"], winner["final_price"],
    )

    allowed, reason = validate_spend(credential, winner["final_price"])
    if not allowed:
        return {
            "session_id": auction_id, "status": "policy_blocked", "reason": reason,
            "all_quotes": quotes, "winner": winner,
            "buyer_agent_id": buyer_agent_id,
            "winner_merchant_agent_id": winner["winner_merchant_agent_id"],
            "winner_product_id": winner["winner_product_id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    saved_vs_listed = round(listed_price - winner["final_price"], 2)
    saved_vs_highest = round(max(q["quote"] for q in valid_quotes) - winner["final_price"], 2)

    return {
        "session_id": auction_id,
        "status": "settled",
        "item": item,
        "anchor_product_id": anchor_product_id,
        "listed_price": listed_price,
        "all_quotes": quotes,
        "valid_quotes_count": len(valid_quotes),
        "winner": winner,
        "final_price": winner["final_price"],
        "buyer_agent_id": buyer_agent_id,
        "winner_merchant_agent_id": winner["winner_merchant_agent_id"],
        "winner_product_id": winner["winner_product_id"],
        "savings_vs_listed": saved_vs_listed,
        "savings_vs_highest_quote": saved_vs_highest,
        "buyer_priorities": buyer_priorities,
        "merchants_competed": len(shortlist),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
