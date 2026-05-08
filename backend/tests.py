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
