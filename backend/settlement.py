"""
Module 3: Payment Settlement + Audit Trail
- Signed transaction receipt after negotiation settles
- Full audit log of every event
- Human can revoke any unsettled session
"""

import uuid
import json
import base64
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend


def create_transaction(session: dict, credential: dict, agent_private_pem: str) -> dict:
    """
    Create a signed transaction receipt.
    Agent signs the transaction with its private key — creates non-repudiation.
    """
    txn_payload = {
        "txn_id": f"txn_{uuid.uuid4().hex[:16]}",
        "session_id": session["session_id"],
        "buyer_agent_id": credential["agent_id"],
        "owner_id": credential["owner_id"],
        "item": session["item"],
        "amount": session["final_price"],
        "currency": credential["policy"]["currency"],
        "settled_at": datetime.utcnow().isoformat(),
        "policy_id": credential["agent_id"],  # links back to delegation
    }

    # Agent signs the transaction
    private_key = serialization.load_pem_private_key(
        agent_private_pem.encode(),
        password=None,
        backend=default_backend()
    )
    payload_bytes = json.dumps(txn_payload, sort_keys=True).encode()
    signature = private_key.sign(payload_bytes, padding.PKCS1v15(), hashes.SHA256())
    txn_payload["agent_signature"] = base64.b64encode(signature).decode()

    return txn_payload


def build_audit_log(session: dict, transaction: dict | None) -> list[dict]:
    """
    Build a human-readable audit trail of everything that happened.
    Every offer, counter, accept, and payment is logged.
    """
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
        # Auction round — has quotes + winner instead of buyer_offer
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
            # Regular negotiation round
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

    # Bootstrap
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

    # Negotiate
    session = run_negotiation(
        item="Dev Tools Subscription",
        listed_price=750.0,
        initial_offer=500.0,
        credential=credential
    )

    # Settle + audit
    transaction = None
    if session["status"] == "settled":
        transaction = create_transaction(session, credential, agent_priv)

    logs = build_audit_log(session, transaction)
    print_audit_report(logs, transaction)
