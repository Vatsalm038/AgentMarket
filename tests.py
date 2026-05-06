"""
Tests for Agentic Commerce Protocol
Run with: pytest tests.py -v

These tests cover identity, policy, spend validation, and auction logic
without needing a database or API keys.
"""

import pytest
import json
import uuid
from identity import (
    generate_agent_id, generate_keypair, sign_policy,
    verify_policy_signature, create_agent_credential, validate_spend
)


# ── Identity Tests ──────────────────────────────────────────────────────────

def test_agent_id_format():
    agent_id = generate_agent_id()
    assert agent_id.startswith("did:agent:")
    assert len(agent_id) == len("did:agent:") + 32


def test_keypair_generation():
    private_pem, public_pem = generate_keypair()
    assert "PRIVATE KEY" in private_pem
    assert "PUBLIC KEY" in public_pem


def test_policy_signing_and_verification():
    private_pem, public_pem = generate_keypair()
    agent_id = generate_agent_id()

    policy = {
        "agent_id": agent_id,
        "max_per_txn": 500.0,
        "max_per_day": 2000.0,
        "currency": "INR",
        "allow_auto_renew": False,
        "categories": "saas"
    }

    signature = sign_policy(private_pem, policy)
    assert isinstance(signature, str)
    assert len(signature) > 0

    # Valid signature should verify
    assert verify_policy_signature(public_pem, policy, signature) is True


def test_tampered_policy_fails_verification():
    private_pem, public_pem = generate_keypair()
    agent_id = generate_agent_id()

    policy = {
        "agent_id": agent_id,
        "max_per_txn": 500.0,
        "max_per_day": 2000.0,
        "currency": "INR",
        "allow_auto_renew": False,
        "categories": "saas"
    }

    signature = sign_policy(private_pem, policy)

    # Tamper with policy after signing
    tampered_policy = dict(policy)
    tampered_policy["max_per_txn"] = 99999.0

    # Tampered policy should fail verification
    assert verify_policy_signature(public_pem, tampered_policy, signature) is False


def test_wrong_key_fails_verification():
    private_pem, public_pem = generate_keypair()
    _, wrong_public = generate_keypair()   # different keypair
    agent_id = generate_agent_id()

    policy = {
        "agent_id": agent_id,
        "max_per_txn": 500.0,
        "max_per_day": 2000.0,
        "currency": "INR",
        "allow_auto_renew": False,
        "categories": "*"
    }

    signature = sign_policy(private_pem, policy)
    assert verify_policy_signature(wrong_public, policy, signature) is False


def test_credential_creation():
    private_pem, public_pem = generate_keypair()
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

    sig = sign_policy(private_pem, policy)
    credential = create_agent_credential(agent_id, owner_id, policy, sig)

    assert credential["credential_type"] == "AgentSpendingDelegation"
    assert credential["agent_id"] == agent_id
    assert credential["owner_id"] == owner_id
    assert credential["policy"]["max_per_txn"] == 800.0


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
    return create_agent_credential(agent_id, "user:test", policy, sig)


def test_valid_spend_allowed():
    credential = make_test_credential(max_per_txn=500.0, max_per_day=2000.0)
    allowed, reason = validate_spend(credential, 300.0, daily_spent=0.0)
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
    allowed, reason = validate_spend(credential, 500.0, daily_spent=0.0)
    assert allowed is True


def test_spend_zero_blocked():
    """Zero spend should not be blocked by limits."""
    credential = make_test_credential(max_per_txn=500.0, max_per_day=2000.0)
    allowed, reason = validate_spend(credential, 0.0, daily_spent=0.0)
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
