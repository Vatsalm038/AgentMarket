"""
Module: Buyer-intent matcher (ticket 2.1)

Scores buyer queries against the seeded product catalog and returns ranked
anchor candidates. Distinct from auction._shortlist_competitors: this picks
*one anchor* from a free-text query; auction expands that anchor into a
competitor set keyed off category (ADR-011).

Algorithm (deterministic, no LLM at score time):
  1. SQL filter: active products + merchants, floor_price <= max_price.
  2. Embed the query via OpenAI text-embedding-3-small (ADR-002).
  3. Cosine similarity in numpy over JSONB embeddings (ADR-009).
  4. Haversine distance to each merchant (km).
  5. Weighted score; sort desc; take top_n.

The matcher reads only — caller owns the transaction.
"""

from __future__ import annotations

import logging
import math
from typing import Sequence

import numpy as np
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Merchant, Product


logger = logging.getLogger(__name__)

_EMBED_MODEL = "text-embedding-3-small"

# Lazy-init so importing this module (and the FastAPI app) doesn't require
# OPENAI_API_KEY to be set — boot, CI, migrations, and lint all stay clean.
_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client

# Score weights (must sum to 1.0). Tuned for the Mumbai demo:
# similarity dominates because it's the only signal of intent; distance and
# price are tie-breakers within a roughly relevant set.
W_SIM = 0.6
W_DIST = 0.25
W_PRICE = 0.15
# Mumbai's east-west extent is roughly 25km; 30km saturates distance penalty.
_DIST_SATURATION_KM = 30.0


class MatcherEmbeddingError(RuntimeError):
    """Raised when the OpenAI embedding call fails. Caller decides whether to
    surface a 503 to the user or fall back — never silently return unranked
    rows (CLAUDE.md rule 4: never trust LLM math, but also: don't paper over
    a missing signal)."""


# ── Pure helpers (unit-tested) ──────────────────────────────────────────────

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two (lat, lon) points.

    Pure function; no Earth-flatness shortcuts because Mumbai's auction radius
    (~30km) is small enough that floating-point haversine is exact to <1m."""
    R = 6371.0088  # mean Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _score(
    similarity: float,
    distance_km: float | None,
    listed_price: float,
    max_price: float,
    has_location: bool,
) -> float:
    """Blend similarity / distance / price into a single [0,1] score.

    When the caller has no buyer location, the distance weight redistributes
    to similarity + price proportionally (so the blend still sums to 1.0).
    Pure function; no logging, no DB, no LLM."""
    sim_n = max(0.0, min(1.0, similarity))
    # Price: cheaper is better, capped at the buyer's stated budget. Equal to
    # budget → 0; free → 1. Anything above budget would have been filtered out
    # in SQL already, but clip defensively.
    if max_price <= 0:
        price_n = 0.0
    else:
        price_n = max(0.0, min(1.0, 1.0 - (listed_price / max_price)))

    if has_location and distance_km is not None:
        dist_n = max(0.0, 1.0 - distance_km / _DIST_SATURATION_KM)
        return W_SIM * sim_n + W_DIST * dist_n + W_PRICE * price_n

    # No location signal: split W_DIST proportionally between sim and price so
    # the scale stays [0,1] and the relative weighting between the two
    # remaining components is preserved.
    remaining = W_SIM + W_PRICE
    w_sim = W_SIM + W_DIST * (W_SIM / remaining)
    w_price = W_PRICE + W_DIST * (W_PRICE / remaining)
    return w_sim * sim_n + w_price * price_n


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D vectors. Returns 0.0 if either has
    zero norm (defensive — shouldn't happen with OpenAI embeddings)."""
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ── OpenAI embed wrapper ────────────────────────────────────────────────────

async def _embed_query(query: str) -> list[float]:
    """Embed `query` with the canonical embedding model. Raises
    MatcherEmbeddingError on any client error so the caller can decide
    failure mode instead of receiving silently-unranked rows."""
    try:
        resp = await _get_openai_client().embeddings.create(model=_EMBED_MODEL, input=query)
    except Exception as exc:  # noqa: BLE001 — wrap any OpenAI/network error
        raise MatcherEmbeddingError(f"embedding failed: {exc}") from exc
    return resp.data[0].embedding


# ── Public entry point ──────────────────────────────────────────────────────

async def shortlist_anchors(
    session: AsyncSession,
    query: str,
    buyer_lat: float | None,
    buyer_lon: float | None,
    max_price: float,
    top_n: int = 5,
) -> list[dict]:
    """Rank seeded products against `query` and return the top anchors.

    Returns a list of dicts shaped for downstream consumers:
      product_id, merchant_id, merchant_name, name, listed_price,
      floor_price, distance_km, similarity, score.
    Highest blended score first. Returns [] if no rows clear the filter.
    """
    has_location = buyer_lat is not None and buyer_lon is not None

    # One JOIN, eager — keep round-trips at one. floor_price filter keeps the
    # in-Python similarity scan bounded even when the catalog grows.
    stmt = (
        select(Product, Merchant)
        .join(Merchant, Merchant.id == Product.merchant_id)
        .where(
            Product.is_active.is_(True),
            Product.floor_price <= max_price,
        )
    )
    rows: Sequence[tuple[Product, Merchant]] = (await session.execute(stmt)).all()
    if not rows:
        return []

    # Embed once. If the API is down, raise rather than rank by distance alone —
    # silently dropping similarity would invert the score's meaning.
    query_vec = np.asarray(await _embed_query(query), dtype=np.float64)

    skipped_no_embedding = 0
    skipped_wrong_model = 0
    scored: list[dict] = []

    for product, merchant in rows:
        if product.embedding is None:
            skipped_no_embedding += 1
            continue
        if product.embedding_model != _EMBED_MODEL:
            skipped_wrong_model += 1
            continue

        prod_vec = np.asarray(product.embedding, dtype=np.float64)
        if prod_vec.shape != query_vec.shape:
            # Dimension mismatch — almost certainly a stale embedding from a
            # different model. Treat as wrong-model so we don't crash on dot().
            skipped_wrong_model += 1
            continue

        sim = _cosine(query_vec, prod_vec)
        if has_location:
            dist_km = _haversine_km(buyer_lat, buyer_lon, merchant.lat, merchant.lng)
        else:
            dist_km = None

        listed = float(product.listed_price)
        score = _score(sim, dist_km, listed, max_price, has_location)

        scored.append({
            "product_id": product.id,
            "merchant_id": merchant.id,
            "merchant_name": merchant.name,
            "name": product.name,
            "listed_price": listed,
            "floor_price": float(product.floor_price),
            "distance_km": round(dist_km, 3) if dist_km is not None else None,
            "similarity": round(sim, 6),
            "score": round(score, 6),
        })

    if skipped_no_embedding or skipped_wrong_model:
        logger.warning(
            "matcher_skipped query=%r no_embedding=%d wrong_model=%d "
            "candidates_scored=%d",
            query, skipped_no_embedding, skipped_wrong_model, len(scored),
        )

    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:top_n]
