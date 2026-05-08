"""Seed real Mumbai merchants and products for the MVP demo.

Idempotent: deterministic IDs + ON CONFLICT DO NOTHING means re-running the
script never duplicates rows and never errors. Random sampling is seeded per
merchant so the same merchant always picks the same product subset on re-runs.

Run from repo root with the venv:
    /home/vatsal/personal/agent-market/.venv/bin/python -m scripts.seed
(invoke from inside backend/, since the project uses a flat `backend/` layout)
"""

import asyncio
import random
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

# Allow `python -m scripts.seed` from backend/ — keeps imports symmetric with
# the rest of the flat backend layout that tests.py and main.py already use.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import AsyncSessionLocal
from models import Merchant, Product


# ── Merchants ───────────────────────────────────────────────────────────────
# Approximate neighborhood centroids; lat/lng are jittered per merchant so they
# don't all collide on the exact centroid in the matcher's haversine ranking.
_NEIGHBORHOODS = {
    "Andheri West":  (19.1364, 72.8296, "400058"),
    "Andheri East":  (19.1136, 72.8697, "400069"),
    "Bandra West":   (19.0596, 72.8295, "400050"),
    "Bandra East":   (19.0606, 72.8478, "400051"),
    "Powai":         (19.1176, 72.9060, "400076"),
    "Juhu":          (19.1075, 72.8263, "400049"),
    "Lower Parel":   (18.9962, 72.8302, "400013"),
    "Kurla":         (19.0728, 72.8826, "400070"),
    "Dadar":         (19.0186, 72.8421, "400014"),
    "Ghatkopar":     (19.0863, 72.9081, "400077"),
    "Borivali":      (19.2335, 72.8568, "400066"),
    "Malad":         (19.1864, 72.8487, "400064"),
    "Goregaon":      (19.1646, 72.8493, "400062"),
    "Vile Parle":    (19.0997, 72.8460, "400057"),
}

_MERCHANTS: list[tuple[str, str, str, str]] = [
    # (name, specialty, address_street, neighborhood)
    ("Ashok General Stores",       "kirana",      "Shop 4, Lokhandwala Market",        "Andheri West"),
    ("Sai Mobile World",           "mobile",      "12 SV Road, near Andheri Stn",      "Andheri West"),
    ("Krishna Wallets & Bags",     "accessories", "Shop 22, Ground Floor, Suncity",    "Andheri East"),
    ("Modern Stationery Mart",     "stationery",  "8 Linking Road",                    "Bandra West"),
    ("Hira Panna Cloth House",     "clothing",    "Hill Road, opp. Mehboob Studio",    "Bandra West"),
    ("Mahalaxmi Kirana Bhandar",   "kirana",      "Plot 14, Kala Nagar",               "Bandra East"),
    ("Powai Mobile Centre",        "mobile",      "Hiranandani Galleria",              "Powai"),
    ("Galaxy Electricals",         "electrical",  "IIT Market Lane",                   "Powai"),
    ("Juhu Beach Provisions",      "kirana",      "Gulmohar Road",                     "Juhu"),
    ("Trendz Garments",            "clothing",    "JVPD Scheme",                       "Juhu"),
    ("Parel Hardware & Electric",  "electrical",  "Senapati Bapat Marg",               "Lower Parel"),
    ("Star Mobile Accessories",    "accessories", "Phoenix Market Lane",               "Lower Parel"),
    ("Kurla Bazaar Stores",        "mixed",       "LBS Marg, Kurla West",              "Kurla"),
    ("Dadar Cloth Centre",         "clothing",    "Ranade Road",                       "Dadar"),
    ("Shree Ganesh Provision",     "kirana",      "Plaza Cinema Lane",                 "Dadar"),
    ("Ghatkopar Mobile Hub",       "mobile",      "Rajawadi, near Garodia Nagar",      "Ghatkopar"),
    ("Borivali Stationery Depot",  "stationery",  "LT Road, opp. Borivali Stn",        "Borivali"),
    ("Malad Electric & Hardware",  "electrical",  "S V Road, near InOrbit",            "Malad"),
    ("Goregaon Family Mart",       "mixed",       "Aarey Road",                        "Goregaon"),
    ("Vile Parle Cloth & General", "mixed",       "Hanuman Road, near station",        "Vile Parle"),
]

assert len(_MERCHANTS) == 20


# ── Catalog ─────────────────────────────────────────────────────────────────
# (name, category, base_listed_price_inr) — base prices reflect Mumbai retail
# in the ~2025 range. The merchant-level jitter pass adds ±10% so two shops
# selling the same SKU don't quote identical numbers.

_CATALOG: dict[str, list[tuple[str, str, float]]] = {
    "kirana": [
        ("Basmati Rice 5kg",                    "kirana", 720),
        ("Sona Masoori Rice 5kg",               "kirana", 480),
        ("Aashirvaad Atta 10kg",                "kirana", 520),
        ("Fortune Sunflower Oil 1L",            "kirana", 165),
        ("Saffola Gold Oil 1L",                 "kirana", 215),
        ("Tata Salt 1kg",                       "kirana", 28),
        ("Toor Dal 1kg",                        "kirana", 175),
        ("Moong Dal 1kg",                       "kirana", 145),
        ("Chana Dal 1kg",                       "kirana", 95),
        ("Sugar 1kg",                           "kirana", 48),
        ("Maggi 2-min Noodles (12 pack)",       "kirana", 168),
        ("Parle-G Biscuit (10 pack)",           "kirana", 100),
        ("Britannia Good Day (8 pack)",         "kirana", 120),
        ("Amul Butter 500g",                    "kirana", 270),
        ("Amul Cheese Cubes 200g",              "kirana", 130),
        ("Mother Dairy Ghee 1L",                "kirana", 620),
        ("Red Label Tea 500g",                  "kirana", 270),
        ("Bru Coffee 100g",                     "kirana", 215),
        ("Haldiram Bhujia 200g",                "kirana", 75),
        ("Lays Chips Family Pack",              "kirana", 65),
        ("Kurkure 90g",                         "kirana", 30),
        ("Britannia Bread 400g",                "kirana", 50),
        ("Surf Excel 1kg",                      "kirana", 235),
        ("Vim Bar 200g",                        "kirana", 25),
        ("Colgate MaxFresh 150g",               "kirana", 95),
        ("Dettol Soap 125g",                    "kirana", 50),
        ("Lux Soap 100g",                       "kirana", 38),
        ("Harpic 500ml",                        "kirana", 95),
        ("Lizol 500ml",                         "kirana", 105),
        ("Garam Masala 100g",                   "kirana", 70),
        ("Turmeric Powder 200g",                "kirana", 65),
        ("Red Chilli Powder 200g",              "kirana", 75),
        ("Coriander Powder 200g",               "kirana", 60),
        ("Mustard Oil 1L",                      "kirana", 195),
        ("Besan 1kg",                           "kirana", 130),
        ("Poha 500g",                           "kirana", 55),
        ("Rava 1kg",                            "kirana", 60),
        ("Kissan Mixed Fruit Jam 500g",         "kirana", 175),
        ("MTR Sambar Masala 100g",              "kirana", 70),
        ("Patanjali Honey 500g",                "kirana", 230),
    ],
    "mobile": [
        ("Type-C Charger 25W",                  "mobile", 350),
        ("Micro USB Charger 10W",               "mobile", 180),
        ("Lightning Cable 1m (compatible)",     "mobile", 220),
        ("Type-C to Type-C Cable 1m",           "mobile", 280),
        ("Wired Earphones 3.5mm",               "mobile", 250),
        ("Boat Bassheads 100",                  "mobile", 449),
        ("boAt Rockerz 255 Bluetooth",          "mobile", 1499),
        ("OnePlus Bullets Z2",                  "mobile", 1799),
        ("Mi Power Bank 10000mAh",              "mobile", 999),
        ("Ambrane Power Bank 20000mAh",         "mobile", 1499),
        ("Tempered Glass (universal 6.5\")",    "mobile", 150),
        ("Back Cover (universal mid-range)",    "mobile", 199),
        ("Phone Ring Holder",                   "mobile", 99),
        ("Car Phone Mount",                     "mobile", 299),
        ("Selfie Stick with Bluetooth",         "mobile", 399),
        ("OTG Adapter Type-C",                  "mobile", 149),
        ("Memory Card 64GB",                    "mobile", 599),
        ("Memory Card 128GB",                   "mobile", 1099),
        ("USB-C to 3.5mm Adapter",              "mobile", 199),
        ("Wireless Charger 15W",                "mobile", 799),
        ("Bluetooth Speaker (mini)",            "mobile", 699),
        ("JBL Go 3 Speaker",                    "mobile", 2999),
        ("Phone Stand Adjustable",              "mobile", 249),
        ("Earphone Splitter 3.5mm",             "mobile", 99),
        ("USB Hub 4-port",                      "mobile", 449),
    ],
    "accessories": [
        ("Leather Wallet (men)",                "accessories", 599),
        ("Canvas Wallet (men)",                 "accessories", 349),
        ("Ladies Handbag (medium)",             "accessories", 899),
        ("Sling Bag (unisex)",                  "accessories", 699),
        ("Backpack 25L",                        "accessories", 1199),
        ("Laptop Bag 15.6\"",                   "accessories", 999),
        ("Travel Duffel Bag",                   "accessories", 1499),
        ("Belt Leather (men)",                  "accessories", 499),
        ("Wrist Watch (analog men)",            "accessories", 1299),
        ("Wrist Watch (analog women)",          "accessories", 999),
        ("Sunglasses (unisex)",                 "accessories", 599),
        ("Cap (cotton)",                        "accessories", 249),
        ("Umbrella (compact)",                  "accessories", 349),
        ("Raincoat (adult)",                    "accessories", 699),
        ("Card Holder (slim)",                  "accessories", 299),
        ("Keychain (metal)",                    "accessories", 99),
        ("Coin Pouch",                          "accessories", 149),
    ],
    "clothing": [
        ("Cotton T-shirt (men)",                "clothing", 399),
        ("Polo T-shirt (men)",                  "clothing", 599),
        ("Formal Shirt (men)",                  "clothing", 899),
        ("Casual Shirt (men)",                  "clothing", 749),
        ("Jeans Slim Fit (men)",                "clothing", 1299),
        ("Trousers Formal (men)",               "clothing", 1099),
        ("Kurta (men)",                         "clothing", 899),
        ("Kurti (women)",                       "clothing", 749),
        ("Salwar Suit Set (women)",             "clothing", 1499),
        ("Saree (cotton)",                      "clothing", 1299),
        ("Dupatta (cotton)",                    "clothing", 399),
        ("Leggings (women)",                    "clothing", 349),
        ("Track Pants (men)",                   "clothing", 599),
        ("Boys T-shirt 8-12y",                  "clothing", 299),
        ("Girls Frock 6-10y",                   "clothing", 549),
        ("Innerwear Pack of 3 (men)",           "clothing", 449),
        ("Socks Pack of 3 (unisex)",            "clothing", 199),
        ("Towel Cotton Bath",                   "clothing", 349),
        ("Bedsheet Single",                     "clothing", 599),
        ("Bedsheet Double",                     "clothing", 999),
    ],
    "electrical": [
        ("Extension Board 6-socket",            "electrical", 449),
        ("Extension Board 4-socket",            "electrical", 299),
        ("LED Bulb 9W",                         "electrical", 99),
        ("LED Bulb 12W",                        "electrical", 149),
        ("LED Tubelight 20W",                   "electrical", 349),
        ("Eveready AA Batteries (4 pack)",      "electrical", 80),
        ("Eveready AAA Batteries (4 pack)",     "electrical", 70),
        ("9V Battery",                          "electrical", 65),
        ("Multi-plug 3-pin",                    "electrical", 150),
        ("Mixer Grinder 500W",                  "electrical", 2499),
        ("Electric Kettle 1.5L",                "electrical", 899),
        ("Iron Box (dry)",                      "electrical", 799),
        ("Table Fan 12\"",                      "electrical", 1499),
        ("Pedestal Fan 16\"",                   "electrical", 2499),
        ("Emergency LED Light",                 "electrical", 599),
        ("Torch (rechargeable)",                "electrical", 349),
        ("Wire Coil 1.5mm 90m",                 "electrical", 1099),
        ("Switchboard 6-module",                "electrical", 249),
        ("MCB 16A",                             "electrical", 199),
        ("Soldering Iron 25W",                  "electrical", 299),
    ],
    "stationery": [
        ("Classmate Notebook A5 200pg",         "stationery", 75),
        ("Classmate Long Notebook 300pg",       "stationery", 130),
        ("Camlin Pen Pack of 10",               "stationery", 100),
        ("Reynolds 045 Pen Pack of 5",          "stationery", 50),
        ("Pencil Apsara Pack of 10",            "stationery", 60),
        ("Eraser & Sharpener Set",              "stationery", 30),
        ("Geometry Box",                        "stationery", 199),
        ("Stapler small",                       "stationery", 149),
        ("Stapler Pins box",                    "stationery", 35),
        ("A4 Paper Ream 500 sheets",            "stationery", 349),
        ("Sketch Pens Pack of 12",              "stationery", 99),
        ("Crayons Pack of 24",                  "stationery", 89),
        ("File Folder A4",                      "stationery", 49),
        ("Spiral Notebook A5",                  "stationery", 80),
        ("Sticky Notes Pack",                   "stationery", 79),
        ("Glue Stick Fevistik",                 "stationery", 35),
        ("Scissors Office",                     "stationery", 99),
        ("Marker Permanent Pack of 4",          "stationery", 199),
        ("Whiteboard Marker Pack of 4",         "stationery", 179),
        ("Calculator (basic 12-digit)",         "stationery", 349),
    ],
    "kitchenware": [
        ("Steel Tiffin 3-tier",                 "kitchenware", 599),
        ("Pressure Cooker 3L",                  "kitchenware", 1499),
        ("Pressure Cooker 5L",                  "kitchenware", 1899),
        ("Non-stick Tawa 28cm",                 "kitchenware", 699),
        ("Non-stick Kadhai 24cm",               "kitchenware", 899),
        ("Steel Plates Set of 6",               "kitchenware", 749),
        ("Steel Tumblers Set of 6",             "kitchenware", 449),
        ("Casserole Hot Pot 1.5L",              "kitchenware", 599),
        ("Plastic Storage Container Set",       "kitchenware", 449),
        ("Chopping Board",                      "kitchenware", 199),
    ],
}


# Specialty -> which catalog buckets it draws from. "mixed" stocks a wide
# slice; pure shops stay focused so search results look realistic.
_SPECIALTY_BUCKETS: dict[str, tuple[str, ...]] = {
    "kirana":      ("kirana",),
    "mobile":      ("mobile", "accessories"),
    "accessories": ("accessories",),
    "clothing":    ("clothing", "accessories"),
    "electrical":  ("electrical", "kitchenware"),
    "stationery":  ("stationery",),
    "mixed":       ("kirana", "stationery", "kitchenware", "accessories", "electrical"),
}


# Category-specific markup ratios reflect real Indian retail margins:
# kirana is razor-thin, accessories/clothing are fat. floor_price = listed_price * (1 - margin).
_MARGIN_RANGE: dict[str, tuple[float, float]] = {
    "kirana":      (0.05, 0.15),
    "mobile":      (0.20, 0.35),
    "accessories": (0.25, 0.40),
    "clothing":    (0.30, 0.50),
    "electrical":  (0.15, 0.25),
    "stationery":  (0.20, 0.35),
    "kitchenware": (0.20, 0.35),
}


def _round_inr(value: float) -> Decimal:
    """Quantise to 2dp using banker-safe HALF_UP — matches the Numeric(12,2)
    column and avoids float-tail noise leaking into the listed/floor checks."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _make_price_pair(base_inr: float, category: str, rng: random.Random
                     ) -> tuple[Decimal, Decimal]:
    """Return (listed, floor) where listed jitters base by ±10% and floor sits
    inside the category's margin band. Guarantees floor <= listed and listed > 0
    so the products_floor_le_listed and products_listed_positive CHECKs hold.
    """
    jitter = rng.uniform(-0.10, 0.10)
    listed_f = max(1.0, base_inr * (1 + jitter))
    margin_lo, margin_hi = _MARGIN_RANGE.get(category, (0.20, 0.30))
    margin = rng.uniform(margin_lo, margin_hi)
    floor_f = listed_f * (1 - margin)
    listed = _round_inr(listed_f)
    floor = _round_inr(floor_f)
    if floor > listed:
        floor = listed
    if floor <= 0:
        floor = Decimal("1.00")
    return listed, floor


def _merchant_id(idx: int) -> str:
    return f"merch_{idx:03d}"


def _product_id(merchant_id: str, n: int) -> str:
    return f"prod_{merchant_id}_{n:02d}"


def _build_merchant_rows() -> list[dict]:
    rows: list[dict] = []
    for i, (name, specialty, street, hood) in enumerate(_MERCHANTS, start=1):
        lat0, lng0, pincode = _NEIGHBORHOODS[hood]
        # Per-merchant deterministic RNG so the lat/lng jitter is stable across runs.
        rng = random.Random(f"merchant-{i}")
        lat = round(lat0 + rng.uniform(-0.004, 0.004), 6)
        lng = round(lng0 + rng.uniform(-0.004, 0.004), 6)
        phone = "+91 98" + "".join(str(rng.randint(0, 9)) for _ in range(3)) + " " + \
                "".join(str(rng.randint(0, 9)) for _ in range(5))
        rows.append({
            "id": _merchant_id(i),
            "name": name,
            "address": f"{street}, {hood}, Mumbai",
            "city": "Mumbai",
            "pincode": pincode,
            "lat": lat,
            "lng": lng,
            "phone": phone,
            "_specialty": specialty,
        })
    return rows


def _build_product_rows(merchants: list[dict]) -> list[dict]:
    products: list[dict] = []
    for i, m in enumerate(merchants, start=1):
        specialty = m["_specialty"]
        buckets = _SPECIALTY_BUCKETS[specialty]
        pool: list[tuple[str, str, float]] = []
        for b in buckets:
            pool.extend(_CATALOG[b])

        # Deterministic per-merchant sample so re-runs hit the same product set.
        rng = random.Random(f"products-{i}")
        target = rng.randint(30, 50)
        target = min(target, len(pool))
        chosen = rng.sample(pool, target)

        for n, (pname, category, base_price) in enumerate(chosen, start=1):
            listed, floor = _make_price_pair(base_price, category, rng)
            products.append({
                "id": _product_id(m["id"], n),
                "merchant_id": m["id"],
                "name": pname,
                "description": f"{pname} sold by {m['name']}.",
                "listed_price": listed,
                "floor_price": floor,
                "category": category,
                "is_active": True,
            })
    return products


async def seed() -> tuple[int, int]:
    merchants = _build_merchant_rows()
    products = _build_product_rows(merchants)

    async with AsyncSessionLocal() as db:
        try:
            # Strip the helper-only _specialty key before insert — it isn't a column.
            merchant_values = [{k: v for k, v in m.items() if not k.startswith("_")}
                               for m in merchants]

            await db.execute(
                pg_insert(Merchant.__table__)
                .values(merchant_values)
                .on_conflict_do_nothing(index_elements=["id"])
            )
            await db.execute(
                pg_insert(Product.__table__)
                .values(products)
                .on_conflict_do_nothing(index_elements=["id"])
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    return len(merchants), len(products)


def main() -> None:
    n_merchants, n_products = asyncio.run(seed())
    print(f"seeded {n_merchants} merchants, {n_products} products")


if __name__ == "__main__":
    main()
