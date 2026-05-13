#!/bin/bash
# Run this once against a fresh production Postgres to set up the DB.
# Usage: cd backend && bash ../scripts/bootstrap_production.sh
set -e

echo "=== AgentMarket Production Bootstrap ==="
echo "Running migrations..."
alembic upgrade head

echo "Seeding merchants + products..."
python scripts/seed.py

echo "Computing product embeddings (~2 min, ~\$0.001)..."
python scripts/embed_products.py

echo "=== Bootstrap complete. ==="
