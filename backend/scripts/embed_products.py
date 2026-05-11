"""Backfill products.embedding for every seeded row.

Run from backend/:
    /home/vatsal/personal/agent-market/.venv/bin/python -m scripts.embed_products

Idempotent: SELECTs only rows that are NULL or stale relative to the canonical
text-embedding-3-small model (ADR-002 / ADR-009). Re-runs after a clean pass
are a no-op.

Failure mode: a failing batch is logged and skipped — the rest of the catalog
keeps embedding. A summary at the end reports counts + token cost.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Match scripts/seed.py: flat backend/ layout, prepend parent dir to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import AsyncOpenAI
from sqlalchemy import or_, select, update

from database import AsyncSessionLocal
from models import Merchant, Product


logger = logging.getLogger("embed_products")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

EMBED_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100
# text-embedding-3-small pricing as of 2026-05: $0.02 per 1M input tokens.
PRICE_PER_1M_TOKENS_USD = 0.02

_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _build_input_text(product: Product, merchant_name: str) -> str:
    """Compose the embedding input. Each line is conditional on its source value
    being truthy — never feed 'Category: None' or stray separators into the
    embedding."""
    lines: list[str] = [product.name]
    if product.category:
        lines.append(f"Category: {product.category}")
    if merchant_name:
        lines.append(f"Merchant: {merchant_name}")
    if product.description:
        lines.append(f"\n{product.description}")
    return "\n".join(lines)


async def _fetch_pending() -> list[tuple[str, str]]:
    """Return [(product_id, input_text)] for every row needing an embedding."""
    async with AsyncSessionLocal() as db:
        stmt = (
            select(Product, Merchant.name)
            .join(Merchant, Merchant.id == Product.merchant_id)
            .where(
                or_(
                    Product.embedding.is_(None),
                    Product.embedding_model != EMBED_MODEL,
                )
            )
            .order_by(Product.id)
        )
        rows = (await db.execute(stmt)).all()
    return [(p.id, _build_input_text(p, mname)) for p, mname in rows]


async def _embed_batch(inputs: list[str]) -> tuple[list[list[float]], int]:
    """Embed a batch in one OpenAI call. Returns (vectors, total_tokens)."""
    resp = await _client.embeddings.create(model=EMBED_MODEL, input=inputs)
    vectors = [item.embedding for item in resp.data]
    # SDK exposes usage.prompt_tokens for embeddings.
    tokens = int(getattr(resp.usage, "prompt_tokens", 0))
    return vectors, tokens


async def _write_batch(ids: list[str], vectors: list[list[float]]) -> None:
    """Per-batch commit so a mid-run crash leaves earlier batches persisted."""
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        try:
            for pid, vec in zip(ids, vectors):
                await db.execute(
                    update(Product)
                    .where(Product.id == pid)
                    .values(
                        embedding=vec,
                        embedding_model=EMBED_MODEL,
                        embedding_generated_at=now,
                    )
                )
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def main() -> int:
    pending = await _fetch_pending()
    if not pending:
        logger.info("nothing to embed — every product is up-to-date on %s", EMBED_MODEL)
        print("0 embedded, 0 skipped, 0 tokens, $0.00 estimated")
        return 0

    total = len(pending)
    logger.info("embedding %d products in batches of %d", total, BATCH_SIZE)

    embedded = 0
    failed = 0
    total_tokens = 0

    for start in range(0, total, BATCH_SIZE):
        chunk = pending[start:start + BATCH_SIZE]
        ids = [pid for pid, _ in chunk]
        inputs = [text for _, text in chunk]
        try:
            vectors, tokens = await _embed_batch(inputs)
            await _write_batch(ids, vectors)
            embedded += len(chunk)
            total_tokens += tokens
            print(f"[{embedded}/{total}] embedded (+{len(chunk)}, tokens={tokens})")
        except Exception as exc:  # noqa: BLE001 — keep the backfill going
            failed += len(chunk)
            logger.exception("batch failed start=%d size=%d: %s", start, len(chunk), exc)

    est_cost_usd = total_tokens / 1_000_000 * PRICE_PER_1M_TOKENS_USD
    print(
        f"\nSummary: {embedded} embedded, {failed} failed, "
        f"{total_tokens} tokens, ~${est_cost_usd:.4f} USD"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
