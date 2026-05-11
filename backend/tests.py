"""
Tests for Agentic Commerce Protocol
Run with: pytest tests.py -v

These tests cover identity, policy, spend validation, and auction logic
without needing a database or API keys.
"""

import uuid
import base64
from identity import (
    generate_agent_id, generate_merchant_agent_id, generate_keypair,
    sign_policy, verify_policy_signature, create_agent_credential, validate_spend
)


# ── Identity Tests ──────────────────────────────────────────────────────────

def test_agent_id_format():
    agent_id = generate_agent_id()
    assert agent_id.startswith("did:agent:")
    assert len(agent_id) == len("did:agent:") + 32


def test_merchant_agent_id_format():
    mid = generate_merchant_agent_id()
    assert mid.startswith("did:merchant:")
    assert len(mid) == len("did:merchant:") + 32
    # Buyer/merchant DIDs must not collide on prefix (ADR-010 defence-in-depth).
    assert not mid.startswith("did:agent:")


def test_keypair_generation():
    private_b64, public_b64 = generate_keypair()
    # Ed25519 raw keys are exactly 32 bytes each.
    assert len(base64.b64decode(private_b64)) == 32
    assert len(base64.b64decode(public_b64)) == 32
    # Two successive generations must not collide.
    other_private, other_public = generate_keypair()
    assert other_private != private_b64
    assert other_public != public_b64


def test_policy_signing_and_verification():
    private_b64, public_b64 = generate_keypair()
    agent_id = generate_agent_id()

    policy = {
        "agent_id": agent_id,
        "max_per_txn": 500.0,
        "max_per_day": 2000.0,
        "currency": "INR",
        "allow_auto_renew": False,
        "categories": "saas"
    }

    signature = sign_policy(private_b64, policy)
    assert isinstance(signature, str)
    # Ed25519 signatures are exactly 64 bytes.
    assert len(base64.b64decode(signature)) == 64

    assert verify_policy_signature(public_b64, policy, signature) is True


def test_tampered_policy_fails_verification():
    private_b64, public_b64 = generate_keypair()
    agent_id = generate_agent_id()

    policy = {
        "agent_id": agent_id,
        "max_per_txn": 500.0,
        "max_per_day": 2000.0,
        "currency": "INR",
        "allow_auto_renew": False,
        "categories": "saas"
    }

    signature = sign_policy(private_b64, policy)

    tampered_policy = dict(policy)
    tampered_policy["max_per_txn"] = 99999.0

    assert verify_policy_signature(public_b64, tampered_policy, signature) is False


def test_tampered_signature_fails_verification():
    private_b64, public_b64 = generate_keypair()
    policy = {
        "agent_id": generate_agent_id(),
        "max_per_txn": 100.0, "max_per_day": 500.0,
        "currency": "INR", "allow_auto_renew": False, "categories": "*",
    }
    signature = sign_policy(private_b64, policy)
    raw = bytearray(base64.b64decode(signature))
    raw[0] ^= 0xFF  # flip a bit
    tampered_sig = base64.b64encode(bytes(raw)).decode()
    assert verify_policy_signature(public_b64, policy, tampered_sig) is False


def test_wrong_key_fails_verification():
    private_b64, _ = generate_keypair()
    _, wrong_public = generate_keypair()
    agent_id = generate_agent_id()

    policy = {
        "agent_id": agent_id,
        "max_per_txn": 500.0,
        "max_per_day": 2000.0,
        "currency": "INR",
        "allow_auto_renew": False,
        "categories": "*"
    }

    signature = sign_policy(private_b64, policy)
    assert verify_policy_signature(wrong_public, policy, signature) is False


def test_credential_creation():
    private_b64, _ = generate_keypair()
    agent_id = generate_agent_id()
    owner_id = f"user:{uuid.uuid4().hex[:8]}"

    policy = {
        "agent_id": agent_id,
        "max_per_txn": 800.0,
        "max_per_day": 3000.0,
        "currency": "INR",
        "allow_auto_renew": False,
        "categories": "*"
    }

    sig = sign_policy(private_b64, policy)
    policy_id = f"pol_{uuid.uuid4().hex[:8]}"
    credential = create_agent_credential(agent_id, owner_id, policy_id, policy, sig)

    assert credential["credential_type"] == "AgentSpendingDelegation"
    assert credential["agent_id"] == agent_id
    assert credential["owner_id"] == owner_id
    assert credential["policy_id"] == policy_id
    assert credential["policy"]["max_per_txn"] == 800.0


# ── Settlement signing tests ────────────────────────────────────────────────

def test_transaction_signature_round_trip():
    from settlement import create_transaction, verify_transaction_signature

    owner_priv, _ = generate_keypair()
    agent_priv, agent_pub = generate_keypair()
    agent_id = generate_agent_id()
    policy = {
        "agent_id": agent_id, "max_per_txn": 1000.0, "max_per_day": 5000.0,
        "currency": "INR", "allow_auto_renew": False, "categories": "*",
    }
    policy_id = f"pol_{uuid.uuid4().hex[:8]}"
    credential = create_agent_credential(
        agent_id, "user:test", policy_id, policy, sign_policy(owner_priv, policy)
    )
    session = {
        "session_id": "sess_test", "item": "Test", "final_price": 499.0,
    }
    txn, signed_bytes = create_transaction(session, credential, agent_priv)
    assert isinstance(signed_bytes, bytes)
    assert len(base64.b64decode(txn["agent_signature"])) == 64
    assert verify_transaction_signature(agent_pub, txn) is True

    # Receipt must commit to the policy row that authorized the spend (1.4).
    assert txn["policy_id"] == policy_id

    # Tamper amount → verification must fail.
    tampered = dict(txn)
    tampered["amount"] = 1.0
    assert verify_transaction_signature(agent_pub, tampered) is False

    # Tamper policy_id → verification must fail (signature commits to it).
    tampered_pol = dict(txn)
    tampered_pol["policy_id"] = "pol_attacker"
    assert verify_transaction_signature(agent_pub, tampered_pol) is False


def test_signed_bytes_round_trip_via_persisted_payload():
    """The bytes we'd write to signed_receipts.signed_payload must verify against
    the agent's public key — proves persistence layer can't drift from sign-time
    canonicalization."""
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from settlement import create_transaction

    owner_priv, _ = generate_keypair()
    agent_priv, agent_pub = generate_keypair()
    agent_id = generate_agent_id()
    policy = {
        "agent_id": agent_id, "max_per_txn": 1000.0, "max_per_day": 5000.0,
        "currency": "INR", "allow_auto_renew": False, "categories": "*",
    }
    policy_id = f"pol_{uuid.uuid4().hex[:8]}"
    credential = create_agent_credential(
        agent_id, "user:test", policy_id, policy, sign_policy(owner_priv, policy)
    )
    session = {"session_id": "sess_persist", "item": "X", "final_price": 250.0}
    txn, signed_bytes = create_transaction(session, credential, agent_priv)

    pub_raw = base64.b64decode(agent_pub)
    sig_raw = base64.b64decode(txn["agent_signature"])
    pk = ed25519.Ed25519PublicKey.from_public_bytes(pub_raw)
    pk.verify(sig_raw, signed_bytes)  # raises if invalid


def test_credential_policy_id_flows_into_receipt():
    """1.4 regression: receipt's policy_id must come from the credential, not
    fall back to agent_id (the prior placeholder bug)."""
    from settlement import create_transaction

    owner_priv, _ = generate_keypair()
    agent_priv, _ = generate_keypair()
    agent_id = generate_agent_id()
    policy_id = f"pol_{uuid.uuid4().hex[:8]}"
    policy = {
        "agent_id": agent_id, "max_per_txn": 1000.0, "max_per_day": 5000.0,
        "currency": "INR", "allow_auto_renew": False, "categories": "*",
    }
    credential = create_agent_credential(
        agent_id, "user:test", policy_id, policy, sign_policy(owner_priv, policy)
    )
    session = {"session_id": "sess_link", "item": "X", "final_price": 100.0}
    txn, _signed = create_transaction(session, credential, agent_priv)

    assert txn["policy_id"] == policy_id
    assert txn["policy_id"] != agent_id
    assert txn["policy_id"] == credential["policy_id"]


# ── Idempotency payload-hash helper ─────────────────────────────────────────

def test_payload_hash_is_deterministic():
    from main import _payload_hash, NegotiateRequest

    a = NegotiateRequest(buyer_agent_id="did:agent:abc", agent_private_key="k",
                         item="Tea", listed_price=100.0, initial_offer=50.0)
    b = NegotiateRequest(buyer_agent_id="did:agent:abc", agent_private_key="k",
                         item="Tea", listed_price=100.0, initial_offer=50.0)
    assert _payload_hash(a) == _payload_hash(b)


def test_payload_hash_is_value_sensitive():
    from main import _payload_hash, NegotiateRequest

    a = NegotiateRequest(buyer_agent_id="did:agent:abc", agent_private_key="k",
                         item="Tea", listed_price=100.0, initial_offer=50.0)
    b = NegotiateRequest(buyer_agent_id="did:agent:abc", agent_private_key="k",
                         item="Tea", listed_price=100.0, initial_offer=51.0)
    assert _payload_hash(a) != _payload_hash(b)


def test_idempotency_decide_miss():
    from main import _idempotency_decide, _IdempotencyDecision
    assert _idempotency_decide(None, "h") is _IdempotencyDecision.MISS


def test_idempotency_decide_replay():
    from main import _idempotency_decide, _IdempotencyDecision
    from models import IdempotencyKey

    row = IdempotencyKey(
        endpoint="/x", key="k", request_hash="h",
        response_json={"ok": 1}, status_code=200,
        expires_at=None,
    )
    assert _idempotency_decide(row, "h") is _IdempotencyDecision.HIT_REPLAY


def test_idempotency_decide_mismatch():
    from main import _idempotency_decide, _IdempotencyDecision
    from models import IdempotencyKey

    row = IdempotencyKey(
        endpoint="/x", key="k", request_hash="h_old",
        response_json={"ok": 1}, status_code=200,
        expires_at=None,
    )
    assert _idempotency_decide(row, "h_new") is _IdempotencyDecision.HIT_MISMATCH


def test_idempotency_decide_pending():
    """NULL response_json is the in-flight sentinel — hash matches, body is missing."""
    from main import _idempotency_decide, _IdempotencyDecision
    from models import IdempotencyKey

    row = IdempotencyKey(
        endpoint="/x", key="k", request_hash="h",
        response_json=None, status_code=None,
        expires_at=None,
    )
    assert _idempotency_decide(row, "h") is _IdempotencyDecision.HIT_PENDING


def test_payload_hash_is_field_order_independent():
    """Pydantic field declaration order doesn't affect canonical-JSON hash —
    canonicalization sorts keys, so two equivalent dicts must hash identically."""
    from main import _payload_hash, NegotiateRequest

    a = NegotiateRequest(buyer_agent_id="did:agent:abc", agent_private_key="k",
                         item="Tea", listed_price=100.0, initial_offer=50.0)
    # Build with kwargs in different order — should still produce identical
    # canonical JSON because sort_keys=True normalises ordering.
    b = NegotiateRequest(initial_offer=50.0, listed_price=100.0, item="Tea",
                         agent_private_key="k", buyer_agent_id="did:agent:abc")
    assert _payload_hash(a) == _payload_hash(b)


# ── Spend Validation Tests ──────────────────────────────────────────────────

def make_test_credential(max_per_txn=500.0, max_per_day=2000.0):
    """Helper to create a test credential quickly."""
    private_pem, _ = generate_keypair()
    agent_id = generate_agent_id()
    policy = {
        "agent_id": agent_id,
        "max_per_txn": max_per_txn,
        "max_per_day": max_per_day,
        "currency": "INR",
        "allow_auto_renew": False,
        "categories": "*"
    }
    sig = sign_policy(private_pem, policy)
    policy_id = f"pol_{uuid.uuid4().hex[:8]}"
    return create_agent_credential(agent_id, "user:test", policy_id, policy, sig)


def test_valid_spend_allowed():
    credential = make_test_credential(max_per_txn=500.0, max_per_day=2000.0)
    allowed, _ = validate_spend(credential, 300.0, daily_spent=0.0)
    assert allowed is True


def test_spend_exceeds_per_txn_blocked():
    credential = make_test_credential(max_per_txn=500.0, max_per_day=2000.0)
    allowed, reason = validate_spend(credential, 600.0, daily_spent=0.0)
    assert allowed is False
    assert "per-transaction" in reason


def test_spend_exceeds_daily_blocked():
    credential = make_test_credential(max_per_txn=500.0, max_per_day=2000.0)
    allowed, reason = validate_spend(credential, 400.0, daily_spent=1800.0)
    assert allowed is False
    assert "Daily" in reason


def test_spend_exactly_at_limit_allowed():
    credential = make_test_credential(max_per_txn=500.0, max_per_day=2000.0)
    allowed, _ = validate_spend(credential, 500.0, daily_spent=0.0)
    assert allowed is True


def test_spend_zero_blocked():
    """Zero spend should not be blocked by limits."""
    credential = make_test_credential(max_per_txn=500.0, max_per_day=2000.0)
    allowed, _ = validate_spend(credential, 0.0, daily_spent=0.0)
    assert allowed is True


def test_daily_spend_accumulates_correctly():
    credential = make_test_credential(max_per_txn=500.0, max_per_day=1000.0)

    # First transaction: 400 — should pass
    allowed1, _ = validate_spend(credential, 400.0, daily_spent=0.0)
    assert allowed1 is True

    # Second transaction: 400, but daily_spent already 400 — 800 total, still under 1000
    allowed2, _ = validate_spend(credential, 400.0, daily_spent=400.0)
    assert allowed2 is True

    # Third transaction: 400, daily_spent 800 — would hit 1200, over 1000 limit
    allowed3, _ = validate_spend(credential, 400.0, daily_spent=800.0)
    assert allowed3 is False


# ── Razorpay Mock Tests ──────────────────────────────────────────────────────

def test_razorpay_mock_order_created():
    from razorpay_settlement import create_razorpay_order
    order = create_razorpay_order(
        amount_inr=750.0,
        item="Test Item",
        session_id="sess_test",
        agent_id="did:agent:test"
    )
    assert "id" in order
    assert order["amount"] == 75000   # 750 INR = 75000 paise
    assert order["currency"] == "INR"


def test_razorpay_mock_settlement():
    from razorpay_settlement import settle_via_razorpay

    mock_session = {
        "session_id": "sess_test123",
        "item": "Test Subscription",
        "final_price": 499.0,
        "status": "settled"
    }
    mock_credential = {
        "agent_id": "did:agent:testbuyer",
        "owner_id": "user:alice",
        "policy": {"currency": "INR", "max_per_txn": 1000}
    }

    receipt = settle_via_razorpay(mock_session, mock_credential)
    assert receipt["amount_inr"] == 499.0
    assert receipt["amount_paise"] == 49900
    assert "razorpay_order_id" in receipt
    assert receipt["status"] in ("captured", "mock_captured")


# ── Seed price helper tests ─────────────────────────────────────────────────

def test_make_price_pair_respects_floor_le_listed():
    import random as _random
    from scripts.seed import _make_price_pair, _MARGIN_RANGE

    rng = _random.Random(42)
    for category in _MARGIN_RANGE:
        for base in (25, 99, 499, 2499):
            listed, floor = _make_price_pair(base, category, rng)
            assert listed > 0, (category, base, listed)
            assert floor > 0, (category, base, floor)
            assert floor <= listed, (category, base, listed, floor)


def test_make_price_pair_kirana_thinner_margin_than_clothing():
    import random as _random
    from scripts.seed import _make_price_pair

    # Average margin over many draws should reflect the category-specific bands
    # (kirana 5-15% vs clothing 30-50%). One sample is noisy; average 200.
    def avg_margin(category: str, base: float) -> float:
        rng = _random.Random(7)
        margins = []
        for _ in range(200):
            listed, floor = _make_price_pair(base, category, rng)
            margins.append(1 - float(floor) / float(listed))
        return sum(margins) / len(margins)

    assert avg_margin("kirana", 200) < avg_margin("clothing", 200)


# ── Agent skills seed tests ─────────────────────────────────────────────────

def test_agent_skills_seed_shape():
    """All 6 personas must carry the math-clamp placeholders and the JSON
    contract keyword — defense-in-depth for CLAUDE.md rule 4."""
    from scripts.seed import _SKILLS

    assert len(_SKILLS) == 6
    ids = {s["id"] for s in _SKILLS}
    assert len(ids) == 6  # IDs unique
    names = {s["name"] for s in _SKILLS}
    assert len(names) == 6  # names unique (matches DB unique constraint)

    required_placeholders = (
        "{role}", "{counterparty_role}", "{item}",
        "{listed_price}", "{budget_cap}", "{floor_price}",
        "{round_n}", "{max_rounds}", "{prior_offers_json}",
        "{min_response_price}", "{max_response_price}",
    )
    for skill in _SKILLS:
        tpl = skill["system_prompt_template"]
        for ph in required_placeholders:
            assert ph in tpl, (skill["id"], ph)
        assert "JSON" in tpl or "json" in tpl, skill["id"]
        # Markdown fences would defeat strict-JSON parsing in the caller.
        assert "```" not in tpl, skill["id"]


# ── Auction helpers + request shape (1.7) ───────────────────────────────────

def test_auction_clamp_quote_inside_band():
    """_clamp_quote must bound the LLM output to [floor, min(listed, budget)]
    even if the model invents a price outside the band."""
    from auction import _clamp_quote

    # In-band stays put.
    assert _clamp_quote(450.0, floor_price=400.0, listed_price=500.0, buyer_budget=600.0) == 450.0
    # Below floor → floor.
    assert _clamp_quote(100.0, floor_price=400.0, listed_price=500.0, buyer_budget=600.0) == 400.0
    # Above listed → listed (since listed < budget).
    assert _clamp_quote(999.0, floor_price=400.0, listed_price=500.0, buyer_budget=600.0) == 500.0
    # Budget is the binding upper bound when budget < listed.
    assert _clamp_quote(999.0, floor_price=400.0, listed_price=500.0, buyer_budget=450.0) == 450.0
    # Budget below floor — degenerate: clamp pins to floor; outer policy check rejects.
    assert _clamp_quote(300.0, floor_price=400.0, listed_price=500.0, buyer_budget=350.0) == 400.0


def test_auction_request_shape_after_117():
    """1.7 swaps AuctionRequest.item/listed_price for anchor_product_id. Free-text
    item or listed_price on the request must now be a validation error."""
    from pydantic import ValidationError
    from main import AuctionRequest

    # Happy path: anchor_product_id is required and sufficient.
    req = AuctionRequest(
        buyer_agent_id="did:agent:abc",
        agent_private_key="k",
        anchor_product_id="prod_merch_001_01",
    )
    assert req.anchor_product_id == "prod_merch_001_01"
    assert req.num_merchants == 3  # default preserved

    # Missing anchor_product_id must fail.
    try:
        AuctionRequest(buyer_agent_id="did:agent:abc", agent_private_key="k")
    except ValidationError:
        pass
    else:
        raise AssertionError("anchor_product_id should be required")


def test_stable_seed_reproducible():
    """Same inputs → same int; different inputs → different ints. Replay (2.9)
    depends on this being deterministic."""
    from auction import _stable_seed

    s1 = _stable_seed("auction_abc", "merchant_1", "quote")
    s2 = _stable_seed("auction_abc", "merchant_1", "quote")
    assert s1 == s2

    s3 = _stable_seed("auction_abc", "merchant_2", "quote")
    assert s1 != s3

    s4 = _stable_seed("auction_xyz", "merchant_1", "quote")
    assert s1 != s4

    # int63 positive range — must fit in BigInteger (replay_seed column).
    assert 0 <= s1 < (1 << 63)


def test_shortlist_dedup_on_duplicate_merchant_agent():
    """If the same merchant_agent appears in multiple join rows (e.g. multiple
    products), the dedup at line ~113 must drop subsequent occurrences. Pure
    unit test using a mocked session.execute."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from auction import _shortlist_competitors

    anchor = MagicMock()
    anchor.id = "prd_1"
    anchor.category = "kirana"

    def make_row(product_id, magent_id):
        p = MagicMock()
        p.id = product_id
        p.merchant_id = "mer_1"
        p.name = f"Product {product_id}"
        p.listed_price = 100
        p.floor_price = 50
        p.category = "kirana"
        m = MagicMock()
        m.id = "mer_1"
        m.name = "Merchant 1"
        a = MagicMock()
        a.id = magent_id
        s = MagicMock()
        s.id = "skl_1"
        s.name = "Skill 1"
        s.system_prompt_template = "tpl"
        return (p, m, a, s)

    db = AsyncMock()
    anchor_result = MagicMock()
    anchor_result.scalar_one_or_none.return_value = anchor

    shortlist_result = MagicMock()
    # Same merchant_agent_id appears twice → second occurrence must be dropped.
    shortlist_result.all.return_value = [
        make_row("prd_1", "magent_1"),
        make_row("prd_2", "magent_1"),
        make_row("prd_3", "magent_2"),
    ]
    db.execute.side_effect = [anchor_result, shortlist_result]

    rows = asyncio.run(_shortlist_competitors(db, "prd_1", policy_max=1000.0, num_merchants=5))
    magent_ids = [r["merchant_agent_id"] for r in rows]
    assert magent_ids.count("magent_1") == 1
    assert "magent_2" in magent_ids


def test_anchor_always_included_when_within_budget():
    """The anchor must be force-prepended even if it's not in the top-N cheapest."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from auction import _shortlist_competitors

    anchor = MagicMock()
    anchor.id = "prd_anchor"
    anchor.category = "kirana"

    def make_row(product_id, floor_price, magent_id):
        p = MagicMock()
        p.id = product_id
        p.name = f"Product {product_id}"
        p.listed_price = 100
        p.floor_price = floor_price
        p.category = "kirana"
        m = MagicMock()
        m.id = f"mer_{magent_id}"
        m.name = f"Merchant {magent_id}"
        a = MagicMock()
        a.id = magent_id
        s = MagicMock()
        s.id = "skl_1"
        s.name = "Skill 1"
        s.system_prompt_template = "tpl"
        return (p, m, a, s)

    db = AsyncMock()
    anchor_result = MagicMock()
    anchor_result.scalar_one_or_none.return_value = anchor

    # First query: top-N by floor — anchor NOT in this set.
    shortlist_result = MagicMock()
    shortlist_result.all.return_value = [
        make_row("prd_cheap1", 10, "magent_a"),
        make_row("prd_cheap2", 20, "magent_b"),
    ]
    # Second query: anchor row fetched separately for force-include.
    anchor_join_result = MagicMock()
    anchor_join_result.first.return_value = make_row("prd_anchor", 80, "magent_anchor")

    db.execute.side_effect = [anchor_result, shortlist_result, anchor_join_result]

    rows = asyncio.run(_shortlist_competitors(db, "prd_anchor", policy_max=1000.0, num_merchants=2))
    assert rows[0]["product_id"] == "prd_anchor", "anchor must be at index 0"
    assert len(rows) <= 2  # cap respected


def test_auction_anchor_unaffordable_returns_failure():
    """If anchor's floor_price > policy_max, run_auction must short-circuit with
    a clear failure dict and NEVER call the LLM. Verified by stubbing the DB
    shortlist to return an unaffordable anchor row."""
    import asyncio
    from unittest.mock import AsyncMock, patch
    import auction as auction_mod

    fake_shortlist = [{
        "product_id": "prd_anchor",
        "product_name": "Premium Widget",
        "listed_price": 5000.0,
        "floor_price": 1500.0,  # exceeds policy_max below
        "category": "kirana",
        "merchant_id": "mer_1",
        "merchant_name": "Merchant 1",
        "merchant_agent_id": "magent_1",
        "skill_id": "skl_1",
        "skill_name": "Skill",
        "system_prompt_template": "tpl",
    }]

    credential = {
        "agent_id": "did:agent:test",
        "policy_id": "pol_test",
        "policy": {"max_per_txn": 1000.0, "currency": "INR"},
    }

    async def fake_shortlist_competitors(*args, **kwargs):
        return fake_shortlist

    # Spy on the LLM helper to assert it's never called.
    called = {"merchant_quote": 0, "buyer_eval": 0}

    async def spy_merchant(*a, **kw):
        called["merchant_quote"] += 1
        return {}

    async def spy_buyer(*a, **kw):
        called["buyer_eval"] += 1
        return {}

    db = AsyncMock()
    with patch.object(auction_mod, "_shortlist_competitors", fake_shortlist_competitors), \
         patch.object(auction_mod, "_merchant_initial_quote", spy_merchant), \
         patch.object(auction_mod, "_buyer_evaluate_quotes", spy_buyer):
        result = asyncio.run(auction_mod.run_auction(db, "prd_anchor", credential))

    assert result["status"] == "failed"
    assert result["reason"] == "anchor_unaffordable"
    assert result["anchor_product_id"] == "prd_anchor"
    assert result["anchor_floor_price"] == 1500.0
    assert result["policy_max"] == 1000.0
    assert called["merchant_quote"] == 0, "LLM merchant_quote must not be called"
    assert called["buyer_eval"] == 0, "LLM buyer_eval must not be called"


def test_transaction_amount_is_float_not_decimal():
    """Regression guard: create_transaction must produce a float amount so the
    receipt is JSON-serialisable. Decimal would silently break json.dumps."""
    from settlement import create_transaction

    owner_priv, _ = generate_keypair()
    agent_priv, _ = generate_keypair()
    agent_id = generate_agent_id()
    policy = {
        "agent_id": agent_id, "max_per_txn": 1000.0, "max_per_day": 5000.0,
        "currency": "INR", "allow_auto_renew": False, "categories": "*",
    }
    policy_id = f"pol_{uuid.uuid4().hex[:8]}"
    credential = create_agent_credential(
        agent_id, "user:test", policy_id, policy, sign_policy(owner_priv, policy)
    )
    session = {"session_id": "sess_amount", "item": "X", "final_price": 250.0}
    txn, _signed = create_transaction(session, credential, agent_priv)
    assert isinstance(txn["amount"], float)


if __name__ == "__main__":
    # Run basic smoke test without pytest
    print("Running smoke tests...\n")

    test_agent_id_format()
    print("✓ Agent ID format")

    test_keypair_generation()
    print("✓ Keypair generation")

    test_policy_signing_and_verification()
    print("✓ Policy signing + verification")

    test_tampered_policy_fails_verification()
    print("✓ Tampered policy rejected")

    test_wrong_key_fails_verification()
    print("✓ Wrong key rejected")

    test_valid_spend_allowed()
    print("✓ Valid spend allowed")

    test_spend_exceeds_per_txn_blocked()
    print("✓ Over-limit spend blocked")

    test_spend_exceeds_daily_blocked()
    print("✓ Daily limit enforced")

    test_daily_spend_accumulates_correctly()
    print("✓ Daily accumulation correct")

    test_razorpay_mock_order_created()
    print("✓ Razorpay mock order")

    test_razorpay_mock_settlement()
    print("✓ Razorpay mock settlement")

    print("\nAll smoke tests passed.")
