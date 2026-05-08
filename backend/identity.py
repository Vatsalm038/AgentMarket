"""
Module 1: Agent Identity + Delegation
- Each agent gets a DID + Ed25519 keypair (ADR-001)
- Buyer agents are minted as did:agent:*, merchant agents as did:merchant:* (ADR-010)
- Human owner signs a spending policy (delegation)
- Agent carries a verifiable credential (signed policy)

Key transport format: raw 32-byte Ed25519 keys, base64-encoded as ASCII strings
at the function boundary. The DB stores the raw bytes (BYTEA, octet_length=32);
encoding happens only when keys cross the API surface. Private keys are returned
exactly once at registration and MUST NOT be persisted or logged.
"""

import uuid
import json
import base64
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature


# ── DID generators (ADR-010) ────────────────────────────────────────────────

def generate_agent_id() -> str:
    """Buyer-side agent DID."""
    return f"did:agent:{uuid.uuid4().hex}"


def generate_merchant_agent_id() -> str:
    """Merchant-side agent DID. Distinct prefix prevents cross-table joins
    from silently matching a buyer DID against a merchant DID."""
    return f"did:merchant:{uuid.uuid4().hex}"


# ── Keypair + signing ───────────────────────────────────────────────────────

def generate_keypair() -> tuple[str, str]:
    """Generate an Ed25519 keypair.

    Returns (private_key_b64, public_key_b64) — both 32 bytes base64-encoded.
    The private key is yielded once here and is never persisted by this module.
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_raw = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    return base64.b64encode(private_raw).decode(), base64.b64encode(public_raw).decode()


def _canonical_policy_bytes(policy: dict) -> bytes:
    # sort_keys gives a stable byte-for-byte representation across processes;
    # the same canonical bytes are what ends up in spending_policies.signed_payload.
    return json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()


def sign_policy(private_key_b64: str, policy: dict) -> str:
    """Owner signs a spending policy. Returns base64(signature) — 64 raw bytes."""
    private_raw = base64.b64decode(private_key_b64)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_raw)
    signature = private_key.sign(_canonical_policy_bytes(policy))
    return base64.b64encode(signature).decode()


def verify_policy_signature(public_key_b64: str, policy: dict, signature_b64: str) -> bool:
    """Verify a policy signature. Returns False on any failure (bad key, bad sig,
    tampered payload). Never raises."""
    try:
        public_raw = base64.b64decode(public_key_b64)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_raw)
        signature = base64.b64decode(signature_b64)
        public_key.verify(signature, _canonical_policy_bytes(policy))
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def create_agent_credential(agent_id: str, owner_id: str, policy: dict, signature: str) -> dict:
    """Build the verifiable credential bundle the agent carries in every request."""
    return {
        "credential_type": "AgentSpendingDelegation",
        "version": "1.0",
        "agent_id": agent_id,
        "owner_id": owner_id,
        "issued_at": datetime.utcnow().isoformat(),
        "policy": policy,
        "owner_signature": signature,
    }


def validate_spend(credential: dict, amount: float, daily_spent: float = 0.0) -> tuple[bool, str]:
    """Check if a proposed spend is within policy limits."""
    policy = credential.get("policy", {})
    max_per_txn = policy.get("max_per_txn", 0)
    max_per_day = policy.get("max_per_day", 0)

    if amount > max_per_txn:
        return False, f"Amount {amount} exceeds per-transaction limit {max_per_txn}"

    if (daily_spent + amount) > max_per_day:
        return False, f"Daily limit {max_per_day} would be exceeded (spent: {daily_spent}, new: {amount})"

    return True, "Within policy limits"


# ── Quick demo ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Agent Identity + Delegation Demo (Ed25519) ===\n")

    owner_private, owner_public = generate_keypair()
    owner_id = f"user:{uuid.uuid4().hex[:8]}"
    print(f"Owner ID: {owner_id}")

    agent_id = generate_agent_id()
    agent_private, agent_public = generate_keypair()
    print(f"Buyer DID:    {agent_id}")
    print(f"Merchant DID: {generate_merchant_agent_id()}")

    policy = {
        "agent_id": agent_id,
        "max_per_txn": 500.0,
        "max_per_day": 2000.0,
        "currency": "INR",
        "allow_auto_renew": False,
        "categories": "saas,subscriptions,tools",
    }
    signature = sign_policy(owner_private, policy)
    print(f"\nPolicy signed. Signature length (raw bytes): {len(base64.b64decode(signature))}")

    valid = verify_policy_signature(owner_public, policy, signature)
    print(f"Signature valid: {valid}")

    credential = create_agent_credential(agent_id, owner_id, policy, signature)
    print(f"Credential issued: {credential['credential_type']} v{credential['version']}")

    for amount, daily in [(300.0, 0.0), (600.0, 0.0), (300.0, 1800.0)]:
        allowed, reason = validate_spend(credential, amount, daily)
        status = "ALLOWED" if allowed else "BLOCKED"
        print(f"  Rs.{amount} (daily Rs.{daily}): {status} - {reason}")
