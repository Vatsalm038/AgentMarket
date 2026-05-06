"""
Module 1: Agent Identity + Delegation
- Each agent gets a unique DID + RSA keypair
- Human owner signs a spending policy (delegation)
- Agent carries a verifiable credential (signed policy)
"""

import uuid
import json
import base64
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend


def generate_agent_id() -> str:
    """Generate a DID-style agent identifier."""
    return f"did:agent:{uuid.uuid4().hex}"


def generate_keypair():
    """Generate RSA keypair for agent identity."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    return private_pem, public_pem


def sign_policy(private_key_pem: str, policy: dict) -> str:
    """
    Human owner signs the spending policy.
    Returns base64-encoded signature.
    """
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(),
        password=None,
        backend=default_backend()
    )
    policy_bytes = json.dumps(policy, sort_keys=True).encode()
    signature = private_key.sign(
        policy_bytes,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode()


def verify_policy_signature(public_key_pem: str, policy: dict, signature_b64: str) -> bool:
    """Verify that the policy was signed by the owner's private key."""
    try:
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode(),
            backend=default_backend()
        )
        policy_bytes = json.dumps(policy, sort_keys=True).encode()
        signature = base64.b64decode(signature_b64)
        public_key.verify(
            signature,
            policy_bytes,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False


def create_agent_credential(agent_id: str, owner_id: str, policy: dict, signature: str) -> dict:
    """
    Create a verifiable credential bundle the agent carries in every request.
    This is what gets presented to the merchant agent for trust verification.
    """
    return {
        "credential_type": "AgentSpendingDelegation",
        "version": "1.0",
        "agent_id": agent_id,
        "owner_id": owner_id,
        "issued_at": datetime.utcnow().isoformat(),
        "policy": policy,
        "owner_signature": signature
    }


def validate_spend(credential: dict, amount: float, daily_spent: float = 0.0) -> tuple[bool, str]:
    """
    Check if a proposed spend is within policy limits.
    Returns (allowed: bool, reason: str)
    """
    policy = credential.get("policy", {})
    max_per_txn = policy.get("max_per_txn", 0)
    max_per_day = policy.get("max_per_day", 0)

    if amount > max_per_txn:
        return False, f"Amount {amount} exceeds per-transaction limit {max_per_txn}"

    if (daily_spent + amount) > max_per_day:
        return False, f"Daily limit {max_per_day} would be exceeded (spent: {daily_spent}, new: {amount})"

    return True, "Within policy limits"


# ── Quick demo (run this file directly to see it work) ──────────────────────

if __name__ == "__main__":
    print("=== Agent Identity + Delegation Demo ===\n")

    # 1. Generate owner (human) keypair
    owner_private, owner_public = generate_keypair()
    owner_id = f"user:{uuid.uuid4().hex[:8]}"
    print(f"Owner ID: {owner_id}")

    # 2. Create agent with its own identity
    agent_id = generate_agent_id()
    agent_private, agent_public = generate_keypair()
    print(f"Agent DID: {agent_id}")

    # 3. Owner defines and signs a spending policy
    policy = {
        "agent_id": agent_id,
        "max_per_txn": 500.0,
        "max_per_day": 2000.0,
        "currency": "INR",
        "allow_auto_renew": False,
        "categories": "saas,subscriptions,tools"
    }
    signature = sign_policy(owner_private, policy)
    print(f"\nPolicy signed by owner.")
    print(f"  Max per txn: ₹{policy['max_per_txn']}")
    print(f"  Max per day: ₹{policy['max_per_day']}")

    # 4. Verify signature (as a merchant agent would)
    valid = verify_policy_signature(owner_public, policy, signature)
    print(f"\nSignature valid: {valid}")

    # 5. Build credential bundle
    credential = create_agent_credential(agent_id, owner_id, policy, signature)
    print(f"\nCredential issued: {credential['credential_type']} v{credential['version']}")

    # 6. Test spend validation
    tests = [
        (300.0, 0.0),      # should pass
        (600.0, 0.0),      # exceeds per-txn
        (300.0, 1800.0),   # exceeds daily
    ]
    print("\nSpend validation tests:")
    for amount, daily in tests:
        allowed, reason = validate_spend(credential, amount, daily)
        status = "✓ ALLOWED" if allowed else "✗ BLOCKED"
        print(f"  ₹{amount} (daily spent ₹{daily}): {status} — {reason}")

    print("\nModule 1 complete. Ready for Module 2: A2A negotiation protocol.")
