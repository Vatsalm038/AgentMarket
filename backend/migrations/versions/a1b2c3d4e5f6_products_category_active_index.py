"""products composite index on (category, is_active)

Revision ID: a1b2c3d4e5f6
Revises: 365bcb27952f
Create Date: 2026-05-11

Adds the composite (category, is_active) index flagged as ADR-011 follow-up.
auction.py's _shortlist_competitors filters on this exact pair on every
negotiate/auction call; without the index every call scans the products heap
(~669 rows today, fine, but the index keeps the query plan honest as the
catalog grows). The 2.1 matcher does not use this index (it filters on
is_active + floor_price only) — listed here for completeness.

Idempotent: uses IF NOT EXISTS so re-runs are safe.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "365bcb27952f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_products_category_is_active "
        "ON products (category, is_active)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_products_category_is_active")
