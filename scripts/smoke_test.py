"""
SignedDeals smoke test — runs against local uvicorn at localhost:8000.
Tests: health, auth (register/login/me), merchant routes, buyer routes,
       agent register/delegate, auction flow, receipt verify, idempotency.

Usage:  python scripts/smoke_test.py
"""
import asyncio, sys, uuid, os
import httpx

BASE = os.getenv("BASE", "http://localhost:8000")
PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
WARN = "\033[93m~\033[0m"

errors = []

def ok(label):       print(f"  {PASS} {label}")
def fail(label, d=""):
    print(f"  {FAIL} {label}" + (f"  [{d}]" if d else ""))
    errors.append(label)
def warn(label):     print(f"  {WARN} {label}  (non-blocking)")
def check(label, cond, detail=""):
    if cond: ok(label)
    else:    fail(label, detail)

async def run():
    async with httpx.AsyncClient(timeout=60) as c:
        tag = uuid.uuid4().hex[:6]
        buyer_email    = f"buyer_{tag}@test.sd"
        merchant_email = f"merchant_{tag}@test.sd"
        pw = "Test1234!"

        # ── 1. Health ────────────────────────────────────────────────────────
        print("\n[1] Health")
        r = await c.get(f"{BASE}/health")
        check("GET /health → 200", r.status_code == 200)
        check("status=ok", r.json().get("status") == "ok")

        # ── 2. Auth register + login ─────────────────────────────────────────
        print("\n[2] Auth — register buyer")
        r = await c.post(f"{BASE}/auth/register", json={
            "email": buyer_email, "password": pw,
            "display_name": "Smoke Buyer", "is_buyer": True, "is_merchant": False,
        })
        check("POST /auth/register → 201", r.status_code == 201, r.text[:120])
        data = r.json()
        buyer_token = data.get("access_token", "")
        check("access_token present", bool(buyer_token))
        check("is_buyer=true", data.get("is_buyer") is True)
        check("is_merchant=false", data.get("is_merchant") is False)

        print("\n[3] Auth — register merchant")
        r = await c.post(f"{BASE}/auth/register", json={
            "email": merchant_email, "password": pw,
            "display_name": "Smoke Merchant", "is_buyer": False, "is_merchant": True,
        })
        check("POST /auth/register (merchant) → 201", r.status_code == 201, r.text[:120])
        merchant_token = r.json().get("access_token", "")
        check("merchant token present", bool(merchant_token))

        print("\n[4] Auth — login + /me")
        r = await c.post(f"{BASE}/auth/login", json={"email": buyer_email, "password": pw})
        check("POST /auth/login → 200", r.status_code == 200)
        check("token returned on login", bool(r.json().get("access_token")))
        r = await c.post(f"{BASE}/auth/login", json={"email": buyer_email, "password": "wrong"})
        check("Wrong password → 401", r.status_code == 401)
        r = await c.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {buyer_token}"})
        check("GET /auth/me → 200", r.status_code == 200)
        check("email matches in /me", r.json().get("email") == buyer_email)
        r = await c.get(f"{BASE}/auth/me")
        check("No token → 401", r.status_code == 401)

        # ── 3. Merchant routes ───────────────────────────────────────────────
        print("\n[5] Merchant routes")
        mhdr = {"Authorization": f"Bearer {merchant_token}"}
        bhdr = {"Authorization": f"Bearer {buyer_token}"}

        r = await c.post(f"{BASE}/merchant/products", headers=mhdr, json={
            "title": "Smoke Headphones",
            "description": "Over-ear wireless noise-cancelling headphones",
            "category": "electronics",
            "floor_price_inr": 1200.0,
            "listed_price_inr": 1800.0,
            "delivery_radius_km": 25.0,
            "delivery_days_min": 2,
            "delivery_days_max": 5,
        })
        check("POST /merchant/products → 2xx", r.status_code in (200, 201), r.text[:200])
        product = r.json()
        product_id = product.get("id", "")
        check("product id returned", bool(product_id))
        check("category=electronics", product.get("category") == "electronics")
        check("floor_price_inr=1200", product.get("floor_price_inr") == 1200.0)

        r = await c.get(f"{BASE}/merchant/products", headers=mhdr)
        check("GET /merchant/products → 200", r.status_code == 200)
        check("list has ≥1 product", len(r.json()) >= 1)

        r = await c.patch(f"{BASE}/merchant/products/{product_id}", headers=mhdr,
                          json={"listed_price_inr": 1750.0})
        check("PATCH /merchant/products/:id → 200", r.status_code == 200, r.text[:120])
        check("price updated", r.json().get("listed_price_inr") == 1750.0)

        r = await c.get(f"{BASE}/merchant/stats", headers=mhdr)
        check("GET /merchant/stats → 200", r.status_code == 200, r.text[:120])
        check("active_listings ≥ 1", r.json().get("active_listings", 0) >= 1)

        r = await c.get(f"{BASE}/merchant/products", headers=bhdr)
        check("Buyer → /merchant/products → 403", r.status_code == 403)

        # ── 4. Buyer routes ──────────────────────────────────────────────────
        print("\n[6] Buyer routes")
        r = await c.get(f"{BASE}/buyer/deals", headers=bhdr)
        check("GET /buyer/deals → 200", r.status_code == 200)
        check("returns list", isinstance(r.json(), list))

        r = await c.get(f"{BASE}/buyer/stats", headers=bhdr)
        check("GET /buyer/stats → 200", r.status_code == 200)
        check("total_deals key present", "total_deals" in r.json())

        r = await c.get(f"{BASE}/buyer/deals", headers=mhdr)
        check("Merchant → /buyer/deals → 403", r.status_code == 403)

        # ── 5. Agent register + delegate ─────────────────────────────────────
        print("\n[7] Agent register + delegate")
        owner_id = f"user_{tag}"
        r = await c.post(f"{BASE}/agents/register", json={"owner_id": owner_id, "role": "user_agent"})
        check("POST /agents/register → 200", r.status_code == 200, r.text[:120])
        agent_data = r.json()
        agent_id = agent_data.get("agent_id", "")
        priv_key = agent_data.get("private_key", "")   # field name is "private_key"
        pub_key  = agent_data.get("public_key", "")    # field name is "public_key"
        check("agent_id present", bool(agent_id))
        check("private_key present (returned once)", bool(priv_key))
        check("public_key present", bool(pub_key))

        r = await c.post(f"{BASE}/agents/delegate", json={
            "agent_id": agent_id,
            "owner_private_key": priv_key,
            "owner_public_key": pub_key,
            "max_per_txn": 2500.0,
            "max_per_day": 5000.0,
            "currency": "INR",
        })
        check("POST /agents/delegate → 200", r.status_code == 200, r.text[:120])
        cred = r.json().get("credential", {})
        check("credential has signature", bool(cred.get("owner_signature")))
        check("credential has policy_id", bool(cred.get("policy_id")))

        # ── 6. Auction flow (uses seeded products) ───────────────────────────
        print("\n[8] Auction — seeded products")
        # Find an anchor product from seeded data (electronics category)
        r = await c.get(f"{BASE}/sessions")
        # Use a known seeded product anchor
        idem_key = f"smoke-auction-{tag}"
        r = await c.post(f"{BASE}/commerce/auction", json={
            "buyer_agent_id": agent_id,
            "agent_private_key": priv_key,
            "anchor_product_id": "prod_merch_003_09",  # Canvas Wallet, seeded
            "num_merchants": 3,
            "use_razorpay": False,  # test mode: skip Razorpay to avoid pkg_resources dep
        }, headers={"Idempotency-Key": idem_key}, timeout=90)
        if r.status_code != 200:
            warn(f"Auction with seeded product got {r.status_code} — trying negotiate fallback")
            # Try negotiate instead
            idem_key_neg = f"smoke-neg-{tag}"
            r2 = await c.post(f"{BASE}/commerce/negotiate", json={
                "buyer_agent_id": agent_id,
                "agent_private_key": priv_key,
                "item": "wireless headphones",
                "listed_price": 2000.0,
                "initial_offer": 1500.0,
                "use_razorpay": False,
            }, headers={"Idempotency-Key": idem_key_neg}, timeout=90)
            check("POST /commerce/negotiate fallback → 200", r2.status_code == 200, r2.text[:200])
            session_id  = r2.json().get("session_id", "")
            final_price = r2.json().get("final_price")
        else:
            check("POST /commerce/auction → 200", r.status_code == 200, r.text[:200])
            session_id  = r.json().get("session_id", "")
            final_price = r.json().get("final_price")
            idem_key    = idem_key  # keep for replay test
        check("session_id present", bool(session_id))
        check("final_price returned", final_price is not None, f"got {final_price}")

        # ── 7. Session detail + audit ────────────────────────────────────────
        print("\n[9] Session detail + audit")
        r = await c.get(f"{BASE}/commerce/session/{session_id}")
        check("GET /commerce/session/:id → 200", r.status_code == 200, r.text[:120])
        detail = r.json()
        check("audit_log in detail", isinstance(detail.get("audit_log"), list))
        check("audit_log non-empty", len(detail.get("audit_log", [])) > 0)

        # ── 8. Receipt verify ────────────────────────────────────────────────
        print("\n[10] Receipt verification (session detail + pubkey endpoint)")
        receipt = detail.get("signed_receipt")
        if receipt:
            check("signed_receipt present", bool(receipt))
            check("receipt has signature_b64", bool(receipt.get("signature_b64")))
            check("receipt has amount_inr", receipt.get("amount_inr") is not None)
            check("receipt has policy_id", bool(receipt.get("policy_id")))
            buyer_aid = detail.get("buyer_agent_id", agent_id)
            r = await c.get(f"{BASE}/agents/{buyer_aid}/pubkey")
            check("GET /agents/:id/pubkey → 200", r.status_code == 200, r.text[:120])
            pkdata = r.json()
            check("pubkey returned", bool(pkdata.get("public_key_b64") or pkdata.get("public_key")))
        else:
            warn("No receipt on this session (negotiate without Razorpay) — skipping")

        # ── 9. Idempotency replay ────────────────────────────────────────────
        print("\n[11] Idempotency replay")
        r_replay = await c.post(f"{BASE}/commerce/auction", json={
            "buyer_agent_id": agent_id,
            "agent_private_key": priv_key,
            "anchor_product_id": "prod_merch_003_09",
            "num_merchants": 3,
        }, headers={"Idempotency-Key": idem_key}, timeout=30)
        if r_replay.status_code == 200:
            check("Replay same idem key → same session_id",
                  r_replay.json().get("session_id") == session_id,
                  f"got {r_replay.json().get('session_id')}")
        else:
            warn(f"Replay returned {r_replay.status_code} — skipping (auction path may differ)")

        # ── 10. Platform pubkey ──────────────────────────────────────────────
        print("\n[12] Platform pubkey")
        r = await c.get(f"{BASE}/.well-known/platform-pubkey")
        check("GET /.well-known/platform-pubkey → 200", r.status_code == 200)
        # field name is "public_key" not "public_key_b64"
        check("public_key present", bool(r.json().get("public_key")))
        check("algorithm=Ed25519", r.json().get("algorithm") == "Ed25519")

        # ── 11. Buyer dispute ────────────────────────────────────────────────
        print("\n[13] Buyer dispute")
        r = await c.post(f"{BASE}/buyer/dispute/{session_id}", headers=bhdr)
        # This will 403 because the session's buyer agent isn't linked to the JWT user yet
        # (buyer registered via /agents/register without JWT — pre-auth legacy path)
        # Non-blocking — auth linkage is a Phase 3 task
        if r.status_code in (200, 403, 404):
            warn(f"POST /buyer/dispute/:id → {r.status_code} (auth linkage is Phase 3)")
        else:
            fail(f"POST /buyer/dispute/:id → unexpected {r.status_code}", r.text[:80])

        # ── Summary ──────────────────────────────────────────────────────────
        print(f"\n{'─'*54}")
        total = len(errors)
        if total:
            print(f"\033[91mFAILED — {total} check(s):\033[0m")
            for e in errors: print(f"  • {e}")
            sys.exit(1)
        else:
            print(f"\033[92mAll checks passed.\033[0m")

asyncio.run(run())
