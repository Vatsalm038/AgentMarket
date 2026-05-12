"""AgentMarket MCP server (tickets 2.3 – 2.9).

Boots fastmcp on $MCP_PORT (default 8001) and exposes 6 tools:
  ping, search_local_merchants, negotiate, verify_receipt,
  get_audit_trail, replay_negotiation.

Auth model (intentionally tiny for the MVP demo):
  Claude.ai users don't have AgentMarket accounts. On boot this process
  registers ONE demo buyer agent against /agents/register, captures its
  Ed25519 keypair + delegated policy, and holds them in module-level state.
  All tool calls flow under this single identity. Restart the MCP server →
  fresh agent. The private key is never logged, never returned to Claude,
  and never written to disk. It IS sent to the colocated backend over
  loopback HTTP as part of negotiate() — the backend expects buyer keys
  inline to sign settle-time receipts. This is acceptable only because MCP
  server and backend are co-deployed; for any cross-host or production
  deployment the backend must be refactored to a proof-of-possession nonce
  flow (see backlog Tier 1 — MCP private-key-over-HTTP hardening).

Run from repo root:
    /home/vatsal/personal/agent-market/.venv/bin/python -m mcp_server.server
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from fastmcp import FastMCP

# Make the flat-layout backend importable so DB sessions can be opened
# directly from inside MCP tools (search_local_merchants reads via matcher).
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))

import database  # type: ignore[import-not-found]  # noqa: E402


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MCP_PORT = int(os.getenv("MCP_PORT", "8001"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
VERSION = "0.2.0"
HTTP_TIMEOUT = 60.0
DEMO_MAX_PER_TXN = 2000.0
DEMO_MAX_PER_DAY = 10000.0

mcp = FastMCP(name="agentmarket-mcp")


# ── In-process demo identity ────────────────────────────────────────────────

class _DemoIdentity:
    """Holds the demo buyer's identity for the lifetime of the MCP process.

    Lazily initialised on first tool call (not at import time) so:
      a) `python -m mcp_server.server --help` doesn't hit the network;
      b) the backend doesn't need to be up at import time for tests;
      c) registration cost is paid once and amortised across all tool calls.
    """

    def __init__(self) -> None:
        self.agent_id: str | None = None
        self.public_key_b64: str | None = None
        # Private key is held as raw bytes in memory and used only as a
        # function-local in _build_auction_body. It is never returned by any
        # tool and never persisted. Intentionally not a property to keep the
        # surface trivial to audit.
        self._private_key_b64: str | None = None
        self.credential: dict | None = None
        self.policy_id: str | None = None
        self._init_lock = asyncio.Lock()

    async def ensure_ready(self) -> None:
        if self.agent_id is not None:
            return
        async with self._init_lock:
            if self.agent_id is not None:
                return
            await self._bootstrap()

    async def _bootstrap(self) -> None:
        """Register demo owner + buyer, sign policy. Mirrors demo_endtoend.py
        end-to-end so the MCP flow runs through the exact same code paths as
        the smoke-test script."""
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=HTTP_TIMEOUT) as client:
            r = await client.post(
                "/agents/register",
                json={"owner_id": f"mcp-demo-{uuid.uuid4().hex[:8]}", "role": "user_agent"},
            )
            r.raise_for_status()
            owner = r.json()

            r = await client.post(
                "/agents/register",
                json={"owner_id": f"mcp-demo-{uuid.uuid4().hex[:8]}", "role": "user_agent"},
            )
            r.raise_for_status()
            buyer = r.json()

            r = await client.post(
                "/agents/delegate",
                json={
                    "agent_id": buyer["agent_id"],
                    "owner_private_key": owner["private_key"],
                    "owner_public_key": owner["public_key"],
                    "max_per_txn": DEMO_MAX_PER_TXN,
                    "max_per_day": DEMO_MAX_PER_DAY,
                    "currency": "INR",
                    "allow_auto_renew": False,
                    "categories": "*",
                },
            )
            r.raise_for_status()
            delegated = r.json()

        self.agent_id = buyer["agent_id"]
        self.public_key_b64 = buyer["public_key"]
        self._private_key_b64 = buyer["private_key"]
        self.credential = delegated["credential"]
        self.policy_id = delegated["policy_id"]
        # Log only the agent_id — never the private key.
        logger.info(
            "mcp_demo_agent_ready agent_id=%s policy_id=%s",
            self.agent_id, self.policy_id,
        )


_demo = _DemoIdentity()


# ── HTTP + canonicalisation helpers ─────────────────────────────────────────

def _canonical_bytes(payload: dict) -> bytes:
    """MUST match backend.settlement._canonical_bytes byte-for-byte. Used by
    verify_receipt to recompute the signed bytes from the receipt payload."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _truncate(s: str, n: int = 200) -> str:
    """Squeeze long strings (prompts, signatures) so MCP tool responses stay
    inside Claude's context budget. Reports original length so the caller
    knows what was elided."""
    if s is None:
        return None  # type: ignore[return-value]
    s = str(s)
    if len(s) <= n:
        return s
    return f"{s[:n]}…(len={len(s)})"


async def _backend_get(client: httpx.AsyncClient, path: str) -> Any:
    r = await client.get(path)
    r.raise_for_status()
    return r.json()


# ── Tools ──────────────────────────────────────────────────────────────────

@mcp.tool
async def ping() -> dict:
    """Smoke test: confirms this MCP server is reachable and can in turn reach
    the FastAPI backend's /health over loopback."""
    backend_health: dict | str
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{BACKEND_URL}/health")
            r.raise_for_status()
            backend_health = r.json()
        except Exception as exc:  # noqa: BLE001
            backend_health = f"unreachable: {exc.__class__.__name__}: {exc}"

    return {
        "status": "ok",
        "server": "agentmarket-mcp",
        "version": VERSION,
        "backend_health": backend_health,
        "demo_agent_id": _demo.agent_id,  # None until first non-ping tool call.
    }


@mcp.tool
async def search_local_merchants(
    query: str,
    max_price_inr: float,
    buyer_lat: float | None = None,
    buyer_lon: float | None = None,
    top_n: int = 5,
) -> dict:
    """Find merchants in Mumbai selling something matching `query` under
    `max_price_inr`. Returns ranked anchor products with merchant name,
    distance (if location provided), and price band info.

    Indian context: prices in INR, locations in Mumbai (radius ~30km).
    """
    # Open a fresh session per tool call — tools don't share transactions.
    from matcher import shortlist_anchors  # type: ignore[import-not-found]  # local import: avoid OpenAI client at module load

    async def _run() -> list[dict]:
        async with database.AsyncSessionLocal() as session:
            return await shortlist_anchors(
                session, query, buyer_lat, buyer_lon, max_price_inr, top_n,
            )

    try:
        raw = await asyncio.wait_for(_run(), timeout=30.0)
    except asyncio.TimeoutError:
        return {"results": [], "query": query, "total": 0,
                "error": "matcher timed out after 30s"}

    results = [{
        "product_id": r["product_id"],
        "merchant_name": r["merchant_name"],
        "name": r["name"],
        "listed_price_inr": round(float(r["listed_price"]), 2),
        "floor_price_inr": round(float(r["floor_price"]), 2),
        "distance_km": round(r["distance_km"], 1) if r["distance_km"] is not None else None,
        "similarity": r["similarity"],
        "score": r["score"],
    } for r in raw]
    return {"results": results, "query": query, "total": len(results)}


@mcp.tool
async def negotiate(
    anchor_product_id: str,
    max_price_inr: float | None = None,
    buyer_priorities: str = "lowest price",
    num_merchants: int = 3,
) -> dict:
    """Run a multi-merchant auction for the given anchor product. Buyer is the
    MCP server's demo agent. Spending is capped by the demo policy.

    `max_price_inr`, if provided and BELOW the demo policy's per-txn cap, must
    be re-delegated upstream (this tool does not dynamically rewrite policies);
    returns an error in that case.

    Returns a shrunk summary (final price, winner, session_id) — call
    get_audit_trail / verify_receipt / replay_negotiation for full detail.
    """
    await _demo.ensure_ready()

    if max_price_inr is not None and max_price_inr < DEMO_MAX_PER_TXN:
        return {
            "status": "policy_blocked",
            "reason": (
                f"max_price_inr={max_price_inr} is below the demo policy's "
                f"per-txn cap of INR {DEMO_MAX_PER_TXN}. The MCP server's "
                "policy must be re-delegated to lower the cap dynamically. "
                "For the MVP demo, omit max_price_inr or pass a value >= "
                f"{DEMO_MAX_PER_TXN}."
            ),
        }

    body = {
        "buyer_agent_id": _demo.agent_id,
        "agent_private_key": _demo._private_key_b64,
        "anchor_product_id": anchor_product_id,
        "num_merchants": num_merchants,
        "buyer_priorities": buyer_priorities,
        "use_razorpay": False,
    }
    # Deterministic idempotency key: a retry from Claude with the same inputs
    # must hit the cached response rather than re-running (and re-charging) the
    # auction. CLAUDE.md rule 3.
    idem_seed = json.dumps(
        {
            "agent_id": _demo.agent_id,
            "anchor_product_id": anchor_product_id,
            "max_price_inr": max_price_inr,
            "buyer_priorities": buyer_priorities,
            "num_merchants": num_merchants,
        },
        sort_keys=True, separators=(",", ":"),
    ).encode()
    idem_key = f"mcp-{hashlib.sha256(idem_seed).hexdigest()[:32]}"

    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=HTTP_TIMEOUT) as client:
        try:
            r = await client.post(
                "/commerce/auction", json=body,
                headers={"Idempotency-Key": idem_key},
            )
            r.raise_for_status()
            result = r.json()
        except httpx.HTTPStatusError as exc:
            return {
                "status": "failed",
                "reason": f"backend returned {exc.response.status_code}",
                "detail": exc.response.text[:500],
            }
        except httpx.HTTPError as exc:
            return {
                "status": "failed",
                "reason": f"backend unreachable: {exc.__class__.__name__}: {exc}",
            }

    status = result.get("status", "failed")
    winner = result.get("winner") or {}
    quotes = result.get("all_quotes") or []
    if status != "settled":
        return {
            "status": status,
            "session_id": result.get("session_id"),
            "reason": result.get("reason", "auction did not settle"),
            "anchor_product_id": anchor_product_id,
        }

    return {
        "status": "settled",
        "session_id": result["session_id"],
        "item": result.get("item"),
        "anchor_product_id": anchor_product_id,
        "final_price_inr": result.get("final_price"),
        "listed_price_inr": result.get("listed_price"),
        "savings_vs_listed_inr": result.get("savings_vs_listed"),
        "winner_merchant_name": winner.get("winner_merchant_name"),
        "winner_reason": winner.get("reason"),
        "all_quotes_summary": [
            {"merchant_name": q.get("merchant_name"), "quote_inr": q.get("quote")}
            for q in quotes
        ],
        "audit_entries": result.get("audit_entries"),
        "next_steps": (
            f"Call verify_receipt('{result['session_id']}') to confirm the "
            f"Ed25519 signature, get_audit_trail('{result['session_id']}') "
            f"for the full trail, or replay_negotiation('{result['session_id']}') "
            "to reproduce this auction."
        ),
    }


@mcp.tool
async def verify_receipt(session_id: str) -> dict:
    """Independently verify the Ed25519 signature on the receipt for a settled
    session. Fetches the buyer's public key from the backend (NOT trusted from
    the receipt itself) and re-canonicalises the payload bytes for verify.
    """
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=HTTP_TIMEOUT) as client:
        detail = await _backend_get(client, f"/commerce/session/{session_id}")
        receipt = detail.get("signed_receipt")
        if receipt is None:
            raise RuntimeError(
                f"session {session_id} has no signed_receipt — "
                "either it didn't settle or the backend is older than ticket 2.7"
            )
        buyer_agent_id = receipt["buyer_agent_id"]
        pubkey = await _backend_get(client, f"/agents/{buyer_agent_id}/pubkey")

    # Receipt's payload_json is the txn dict including agent_signature. Strip
    # the signature, recompute canonical bytes, verify against the buyer's pubkey.
    payload = dict(receipt["payload_json"])
    sig_b64 = payload.pop("agent_signature", None)
    if sig_b64 is None:
        raise RuntimeError("receipt payload missing agent_signature field")

    msg = _canonical_bytes(payload)
    pub = ed25519.Ed25519PublicKey.from_public_bytes(
        base64.b64decode(pubkey["public_key"])
    )
    try:
        pub.verify(base64.b64decode(sig_b64), msg)
    except InvalidSignature:
        return {
            "verified": False,
            "session_id": session_id,
            "reason": "Ed25519 signature did not validate against agent's public key",
        }

    return {
        "verified": True,
        "session_id": session_id,
        "agent_id": buyer_agent_id,
        "amount_inr": float(receipt["amount_inr"]),
        "policy_id": receipt["policy_id"],
        "signature_truncated": f"{sig_b64[:16]}…",
        "verification_method": "Ed25519 client-side against /agents/{id}/pubkey",
    }


@mcp.tool
async def get_audit_trail(session_id: str) -> dict:
    """Fetch the full audit log + signed-receipt details for a settled session.

    Useful when the buyer wants to see exactly what was negotiated, by whom,
    for what reason, with what cryptographic proof. Audit events are summarised
    to one line each — call replay_negotiation for the full prompts/responses.
    """
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=HTTP_TIMEOUT) as client:
        detail = await _backend_get(client, f"/commerce/session/{session_id}")

    session = detail["session"]
    audit_log = detail.get("audit_log") or []

    def _summarise(event: str, payload: dict) -> str:
        if event == "session_started":
            return f"started: item={payload.get('item')!r} listed={payload.get('listed_price')}"
        if event == "auction_quotes_collected":
            return f"collected {payload.get('quotes_count', 0)} quotes"
        if event == "auction_winner_selected":
            return (
                f"winner={payload.get('winner')!r} price={payload.get('price')} "
                f"reason={_truncate(str(payload.get('reason', '')), 80)}"
            )
        if event == "payment_settled":
            return f"settled txn={payload.get('txn_id')} amount={payload.get('amount')}"
        if event == "negotiation_failed":
            return f"failed: status={payload.get('status')}"
        return event

    rcpt = detail.get("signed_receipt") or {}
    rcpt_summary = None
    if rcpt:
        sig = rcpt.get("signature_b64") or ""
        rcpt_summary = {
            "signature_truncated": f"{sig[:16]}…" if sig else None,
            "signed_at": rcpt.get("created_at"),
            "agent_id": rcpt.get("buyer_agent_id"),
            "amount_inr": rcpt.get("amount_inr"),
            "razorpay_payment_id": rcpt.get("razorpay_payment_id"),
        }

    return {
        "session_id": session["id"],
        "status": session["status"],
        "item": session["item"],
        "final_price_inr": session.get("final_price"),
        "listed_price_inr": session.get("listed_price"),
        "policy_id": session.get("policy_id"),
        "audit_log": [{
            "event": l["event"],
            "actor": (l.get("payload") or {}).get("agent_id"),
            "timestamp": l["timestamp"],
            "summary": _summarise(l["event"], l.get("payload") or {}),
        } for l in audit_log],
        "signed_receipt": rcpt_summary,
        "replay_metadata": {
            "winner_skill_id": detail.get("winner_skill_id"),
            "llm_seed": detail.get("llm_seed"),
        },
    }


@mcp.tool
async def replay_negotiation(session_id: str) -> dict:
    """Re-run the auction using the persisted prompts + seeds and report
    whether the outputs match. Demonstrates that the auction was deterministic
    and reproducible (ADR-007). Note: OpenAI's `seed` is best-effort; minor
    drift is reported honestly via match=False rather than hidden.
    """
    from openai import AsyncOpenAI  # local import: keeps OpenAI off the boot path

    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=HTTP_TIMEOUT) as client:
        detail = await _backend_get(client, f"/commerce/session/{session_id}")

    replay_data = detail.get("replay_data")
    if not replay_data or not replay_data.get("auction"):
        return {
            "session_id": session_id,
            "match": False,
            "reason": (
                "no replay_data persisted for this session — either it "
                "predates ticket 2.9 or never settled"
            ),
        }

    auction_block = replay_data["auction"]
    model = auction_block.get("model", "gpt-4o-mini")
    temperature = auction_block.get("temperature", 0)

    client = AsyncOpenAI()
    details: list[dict] = []

    async def _replay_one(call_name: str, stored: dict) -> dict:
        resp = await client.chat.completions.create(
            model=stored.get("model", model),
            max_tokens=300,
            temperature=stored.get("temperature", temperature),
            seed=stored.get("seed"),
            messages=[{"role": "user", "content": stored["user_prompt"]}],
        )
        replay_raw = (resp.choices[0].message.content or "").strip()
        original_raw = (stored.get("raw_response") or "").strip()
        return {
            "call": call_name,
            "merchant": stored.get("merchant_name"),
            "seed": stored.get("seed"),
            "original_response": _truncate(original_raw, 200),
            "replay_response": _truncate(replay_raw, 200),
            "match": replay_raw == original_raw,
        }

    for stored in auction_block.get("merchant_quotes", []) or []:
        details.append(await _replay_one("merchant_quote", stored))

    buyer_eval = auction_block.get("buyer_eval")
    if buyer_eval:
        details.append(await _replay_one("buyer_eval", buyer_eval))

    # Compare final prices by re-parsing buyer_eval (LLM-determined) — but the
    # authoritative original_final_price comes from the session row.
    original_final = detail["session"].get("final_price")
    overall_match = all(d["match"] for d in details) if details else False

    return {
        "session_id": session_id,
        "original_final_price_inr": original_final,
        "replay_final_price_inr": original_final if overall_match else None,
        "match": overall_match,
        "note": (
            None if overall_match
            else "Replay outputs diverged from original — OpenAI's seed is "
                 "best-effort. This is surfaced honestly per ADR-007."
        ),
        "details": details,
    }


# ── Entrypoint ──────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("MCP server listening on port %d (backend=%s)", MCP_PORT, BACKEND_URL)
    mcp.run(transport="http", host="127.0.0.1", port=MCP_PORT)


if __name__ == "__main__":
    main()
