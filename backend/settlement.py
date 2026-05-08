"""
Module 3: Payment Settlement + Audit Trail
- Signed transaction receipt after negotiation settles (Ed25519, ADR-001)
- Full audit log of every event
- Human can revoke any unsettled session

Receipt signing uses the buyer agent's Ed25519 private key over the canonical
JSON of the txn payload. The exact bytes signed are what would be persisted to
signed_receipts.signed_payload (see migration 365bcb27952f) so verification
never has to re-canonicalize from columns.
"""

import uuid
import json
import base64
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature


def _canonical_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def create_transaction(session: dict, credential: dict, agent_private_key_b64: str) -> dict:
    """Create a signed transaction receipt. The buyer agent signs with its
    private key — non-repudiation. policy_id is a placeholder until 1.4 wires
    receipts.policy_id to a real spending_policies row."""
    txn_payload = {
        "txn_id": f"txn_{uuid.uuid4().hex[:16]}",
        "session_id": session["session_id"],
        "buyer_agent_id": credential["agent_id"],
        "owner_id": credential["owner_id"],
        "item": session["item"],
        "amount": session["final_price"],
        "currency": credential["policy"]["currency"],
        "settled_at": datetime.utcnow().isoformat(),
        "policy_id": credential["agent_id"],  # 1.4: replace with real policy row id
    }

    private_raw = base64.b64decode(agent_private_key_b64)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_raw)
    signature = private_key.sign(_canonical_bytes(txn_payload))
    txn_payload["agent_signature"] = base64.b64encode(signature).decode()

    return txn_payload


def build_audit_log(session: dict, transaction: dict | None) -> list[dict]:
    """Build a human-readable audit trail of everything that happened."""
    logs = []

    def log(event: str, payload: dict):
        logs.append({
            "log_id": f"log_{uuid.uuid4().hex[:8]}",
            "session_id": session["session_id"],
            "agent_id": session["buyer_agent_id"],
            "event": event,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat()
        })

    log("session_started", {
        "item": session["item"],
        "listed_price": session["listed_price"],
        "initial_offer": session["initial_offer"]
    })

    for r in session.get("rounds", []):
        if r.get("type") == "auction":
            log("auction_quotes_collected", {
                "round": r["round"],
                "quotes_count": len(r.get("quotes", [])),
                "quotes": [{"merchant": q["merchant_name"], "price": q["quote"]}
                           for q in r.get("quotes", [])]
            })
            if r.get("winner"):
                log("auction_winner_selected", {
                    "round": r["round"],
                    "winner": r["winner"].get("winner_merchant_name"),
                    "price": r["winner"].get("final_price"),
                    "reason": r["winner"].get("reason")
                })
        else:
            if "buyer_offer" in r:
                log("offer_sent", {"round": r["round"], "buyer_offer": r["buyer_offer"]})
            if "merchant_action" in r:
                log(f"merchant_{r['merchant_action']}", {
                    "round": r["round"],
                    "price": r.get("merchant_price"),
                    "reason": r.get("merchant_reason")
                })
            if "buyer_counter_action" in r:
                log(f"buyer_{r['buyer_counter_action']}", {
                    "round": r["round"],
                    "price": r.get("buyer_counter_price")
                })

    if session["status"] == "settled" and transaction:
        log("payment_settled", {
            "txn_id": transaction["txn_id"],
            "amount": transaction["amount"],
            "currency": transaction["currency"],
            "signed": True
        })
    else:
        log("negotiation_failed", {"status": session["status"]})

    return logs


def verify_transaction_signature(public_key_b64: str, transaction: dict) -> bool:
    """Verify a receipt's agent_signature against the buyer agent's public key.
    Strips the signature field before recomputing canonical bytes."""
    try:
        sig_b64 = transaction["agent_signature"]
        payload = {k: v for k, v in transaction.items() if k != "agent_signature"}
        public_raw = base64.b64decode(public_key_b64)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_raw)
        public_key.verify(base64.b64decode(sig_b64), _canonical_bytes(payload))
        return True
    except (InvalidSignature, ValueError, TypeError, KeyError):
        return False


def print_audit_report(logs: list[dict], transaction: dict | None):
    """Pretty-print the full audit trail."""
    print(f"\n{'='*55}")
    print("  AUDIT TRAIL")
    print(f"{'='*55}")
    for entry in logs:
        ts = entry["timestamp"].split("T")[1][:8]
        print(f"  [{ts}] {entry['event'].upper()}")
        for k, v in entry["payload"].items():
            print(f"           {k}: {v}")

    if transaction:
        print(f"\n{'='*55}")
        print("  SIGNED TRANSACTION RECEIPT")
        print(f"{'='*55}")
        for k, v in transaction.items():
            if k == "agent_signature":
                print(f"  {k}: {v[:40]}...")
            else:
                print(f"  {k}: {v}")


if __name__ == "__main__":
    from identity import (generate_agent_id, generate_keypair,
                          sign_policy, create_agent_credential)
    from negotiation import run_negotiation

    owner_priv, owner_pub = generate_keypair()
    agent_priv, agent_pub = generate_keypair()
    agent_id = generate_agent_id()
    policy = {
        "agent_id": agent_id,
        "max_per_txn": 800.0,
        "max_per_day": 3000.0,
        "currency": "INR",
        "allow_auto_renew": False,
        "categories": "saas,tools"
    }
    sig = sign_policy(owner_priv, policy)
    credential = create_agent_credential(agent_id, "user:demo", policy, sig)

    session = run_negotiation(
        item="Dev Tools Subscription",
        listed_price=750.0,
        initial_offer=500.0,
        credential=credential
    )

    transaction = None
    if session["status"] == "settled":
        transaction = create_transaction(session, credential, agent_priv)

    logs = build_audit_log(session, transaction)
    print_audit_report(logs, transaction)
