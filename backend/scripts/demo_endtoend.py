"""End-to-end happy-path demo + smoke test for AgentMarket.

Exercises the full Mumbai-wallet-under-INR-500 narrative against a locally
running backend:
  register agent -> delegate policy -> run auction -> verify receipt locally
  -> idempotency replay -> session replay fields.

The receipt's Ed25519 signature is verified IN THIS SCRIPT against the buyer
agent's public key (captured at registration), not by trusting the server.
That independent verify step is the demo's core trust claim.

Anchor choice: `prod_merch_003_09` (Canvas Wallet, Krishna Wallets & Bags,
Andheri East — listed INR 377.19). This product is produced deterministically
by `backend/scripts/seed.py` so the script is reproducible. The merchant sits
in Andheri to match the project-brief narrative ("wallet under INR 500 in
Andheri").

Usage:
    # 1. In one terminal:
    cd /home/vatsal/personal/agent-market
    uvicorn backend.main:app --reload
    # 2. In another:
    cd /home/vatsal/personal/agent-market/backend
    ../.venv/bin/python -m scripts.demo_endtoend
"""

import asyncio
import base64
import json
import sys
import uuid

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519


BASE_URL = "http://localhost:8000"
# Deterministic anchor produced by scripts/seed.py: a sub-INR-500 wallet sold
# by an Andheri merchant. Matches the project-brief narrative line-for-line.
ANCHOR_PRODUCT_ID = "prod_merch_003_09"
# 60s — auction triggers concurrent LLM calls; first run on a cold OpenAI
# connection can sit close to 30s in practice.
TIMEOUT_SECONDS = 60.0
SEP = "=" * 70


def _hr(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")


def _short(s: str, n: int = 8) -> str:
    """Truncate sensitive material (private keys, signatures) for display."""
    return f"{s[:n]}…(len={len(s)})"


def _canonical(payload: dict) -> bytes:
    """Match settlement._canonical_bytes byte-for-byte — must agree so the
    Ed25519 verify lines up with what the server signed."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _verify_receipt_signature(public_key_b64: str, transaction: dict) -> bool:
    """Independent client-side verify. Strips agent_signature, recomputes the
    canonical bytes, and runs Ed25519 verify against the buyer agent's public
    key captured at /agents/register time."""
    # Structural errors (missing field, bad b64) are NOT crypto failures —
    # let them raise so a malformed receipt doesn't masquerade as
    # "signature failed to verify." False only means Ed25519 rejected.
    sig = base64.b64decode(transaction["agent_signature"])
    payload = {k: v for k, v in transaction.items() if k != "agent_signature"}
    pub = ed25519.Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
    try:
        pub.verify(sig, _canonical(payload))
        return True
    except InvalidSignature:
        return False


async def _preflight(client: httpx.AsyncClient) -> None:
    """Fail fast with a clear message if the server isn't running. A bare
    ConnectError from httpx is too cryptic for someone running the demo."""
    try:
        r = await client.get("/health", timeout=5.0)
        r.raise_for_status()
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.HTTPStatusError) as exc:
        print(
            "ERROR: backend is not reachable at "
            f"{BASE_URL} ({exc.__class__.__name__}).\n"
            "Start uvicorn first:\n"
            "  cd /home/vatsal/personal/agent-market && "
            "uvicorn backend.main:app --reload"
        )
        sys.exit(1)


async def _register_agent(client: httpx.AsyncClient) -> dict:
    r = await client.post(
        "/agents/register",
        json={"owner_id": f"user:demo-{uuid.uuid4().hex[:6]}", "role": "user_agent"},
    )
    r.raise_for_status()
    return r.json()


async def _delegate(
    client: httpx.AsyncClient,
    agent_id: str,
    owner_private_b64: str,
    owner_public_b64: str,
) -> dict:
    # Budget sits well above the anchor's listed price (INR 377.19) so the
    # auction has headroom and the policy clamp doesn't dominate the result.
    body = {
        "agent_id": agent_id,
        "owner_private_key": owner_private_b64,
        "owner_public_key": owner_public_b64,
        "max_per_txn": 500.0,
        "max_per_day": 2000.0,
        "currency": "INR",
        "allow_auto_renew": False,
        "categories": "*",
    }
    r = await client.post("/agents/delegate", json=body)
    r.raise_for_status()
    return r.json()


async def _auction(
    client: httpx.AsyncClient,
    agent_id: str,
    agent_private_b64: str,
    idempotency_key: str,
) -> tuple[dict, dict]:
    body = {
        "buyer_agent_id": agent_id,
        "agent_private_key": agent_private_b64,
        "anchor_product_id": ANCHOR_PRODUCT_ID,
        "num_merchants": 3,
        "buyer_priorities": "lowest price",
        # Razorpay is test-mode and demoed separately in ticket 4.1.
        "use_razorpay": False,
    }
    r = await client.post(
        "/commerce/auction",
        json=body,
        headers={"Idempotency-Key": idempotency_key},
    )
    r.raise_for_status()
    return r.json(), dict(r.headers)


async def _session_detail(client: httpx.AsyncClient, session_id: str) -> dict:
    r = await client.get(f"/commerce/session/{session_id}")
    r.raise_for_status()
    return r.json()


async def main() -> int:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT_SECONDS) as client:
        _hr("STEP 1: Preflight /health")
        await _preflight(client)
        print("  backend reachable at", BASE_URL)

        _hr("STEP 2: Register buyer agent (Ed25519 keypair returned once)")
        # Owner keypair is generated server-side by /agents/register too — we
        # reuse the same registration trick: a throwaway owner_agent stands in
        # for a human, so the OWNER signs the policy with its own returned key.
        owner_reg = await _register_agent(client)
        owner_agent_id = owner_reg["agent_id"]
        owner_priv = owner_reg["private_key"]
        owner_pub = owner_reg["public_key"]
        print(f"  owner-side agent_id: {owner_agent_id}")
        print(f"  owner private_key:   {_short(owner_priv)}  [not stored on server]")

        buyer_reg = await _register_agent(client)
        buyer_agent_id = buyer_reg["agent_id"]
        buyer_priv = buyer_reg["private_key"]
        buyer_pub = buyer_reg["public_key"]
        assert buyer_pub, "register response must include public_key"
        assert buyer_priv, "register response must include private_key"
        print(f"  buyer agent_id:      {buyer_agent_id}")
        print(f"  buyer private_key:   {_short(buyer_priv)}  [not stored on server]")
        print(f"  buyer public_key:    {_short(buyer_pub)}")

        _hr("STEP 3: Delegate spending policy (owner signs INR 500/txn cap)")
        # Owner signs with OWNER's private key; the delegate endpoint verifies
        # with the matching public key before persisting.
        delegated = await _delegate(client, buyer_agent_id, owner_priv, owner_pub)
        policy_id = delegated["policy_id"]
        credential = delegated["credential"]
        assert credential["policy_id"] == policy_id, "credential must commit to policy_id"
        print(f"  policy_id:           {policy_id}")
        print(f"  max_per_txn:         INR {credential['policy']['max_per_txn']}")
        print(f"  max_per_day:         INR {credential['policy']['max_per_day']}")

        _hr("STEP 4: Run auction (3 merchants compete on the Andheri wallet)")
        idem_key = f"demo-{uuid.uuid4().hex}"
        print(f"  Idempotency-Key:     {idem_key}")
        print(f"  anchor_product_id:   {ANCHOR_PRODUCT_ID}")
        auction_result, _ = await _auction(client, buyer_agent_id, buyer_priv, idem_key)
        assert auction_result["status"] == "settled", (
            f"auction did not settle: {auction_result}"
        )
        winner = auction_result["winner"]
        print(f"  status:              {auction_result['status']}")
        print(f"  item:                {auction_result['item']}")
        print(f"  listed_price:        INR {auction_result['listed_price']}")
        print(f"  final_price:         INR {auction_result['final_price']}")
        print(f"  winner_merchant:     {winner['winner_merchant_name']}")
        print(f"  winner_reason:       {winner['reason']}")
        print(f"  audit_entries:       {auction_result.get('audit_entries')}")
        session_id = auction_result["session_id"]
        print(f"  session_id:          {session_id}")

        _hr("STEP 5: Independently verify receipt Ed25519 signature")
        transaction = auction_result.get("transaction")
        assert transaction, "settled auction must include a transaction receipt"
        assert transaction.get("policy_id") == policy_id, (
            "receipt must commit to the policy_id that authorized it"
        )
        sig_b64 = transaction["agent_signature"]
        print(f"  txn_id:              {transaction['txn_id']}")
        print(f"  amount:              INR {transaction['amount']}")
        print(f"  policy_id (in rcpt): {transaction['policy_id']}")
        print(f"  signature (b64):     {_short(sig_b64, 12)}")
        ok = _verify_receipt_signature(buyer_pub, transaction)
        assert ok, (
            "Receipt signature failed to verify against the buyer agent's "
            "registered public key. This breaks the demo's trust claim."
        )
        print("  Receipt signature verified against buyer agent's public key")

        _hr("STEP 6: Idempotency replay (same key, same body)")
        replay_result, replay_headers = await _auction(
            client, buyer_agent_id, buyer_priv, idem_key
        )
        assert replay_result == auction_result, (
            "Idempotent replay must return the byte-identical stored response."
        )
        replay_marker = replay_headers.get("idempotent-replay")
        print(f"  Idempotent-Replay header: {replay_marker!r}")
        assert replay_marker == "true", (
            "Backend should set Idempotent-Replay: true on a stored-response replay."
        )
        print("  Idempotency replay works (response byte-identical)")

        _hr("STEP 7: Session record has replay fields")
        detail = await _session_detail(client, session_id)
        session = detail["session"]
        audit_log = detail["audit_log"]
        assert session["id"] == session_id
        assert audit_log, "session detail must include audit_log entries"

        # winner_skill_id and llm_seed are flat columns on the auction winner
        # event payload (settlement.build_audit_log writes them explicitly).
        winner_log = next(
            (e for e in audit_log if e["event"] == "auction_winner_selected"),
            None,
        )
        assert winner_log is not None, "audit_log missing auction_winner_selected event"
        winner_payload = winner_log["payload"]
        assert "winner_skill_id" in winner_payload, "audit_log missing winner_skill_id"
        assert "llm_seed" in winner_payload, "audit_log missing llm_seed"
        print(f"  winner_skill_id:     {winner_payload['winner_skill_id']}")
        print(f"  llm_seed:            {winner_payload['llm_seed']}")
        print(f"  audit events total:  {len(audit_log)}")
        # NOTE: the current /commerce/session/{id} response does not include
        # the persisted signed_receipts row. The receipt verified in STEP 5
        # came from the synchronous /commerce/auction response. Exposing it
        # on the GET is left for a later ticket — flagged but not fixed.
        print("  Session record has replay fields (winner_skill_id + llm_seed in audit_log)")

        _hr("FINAL SUMMARY")
        print(f"  buyer_agent_id:      {buyer_agent_id}")
        print(f"  policy_id:           {policy_id}")
        print(f"  session_id:          {session_id}")
        print(f"  final_price:         INR {auction_result['final_price']}")
        print(f"  receipt verified:    YES  (Ed25519 over canonical txn JSON)")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
