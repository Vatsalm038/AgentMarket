"""
Module 2: A2A Negotiation Protocol
- Buyer agent makes an offer
- Merchant agent (LLM-powered) responds with counter/accept/reject
- Rounds continue until settled or max rounds hit
- Every round is logged to audit trail
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from identity import validate_spend
from openai import OpenAI

logger = logging.getLogger(__name__)

# Lazy-init so importing this module doesn't require OPENAI_API_KEY at boot.
_client: OpenAI | None = None


def _get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


MAX_ROUNDS = 5


def merchant_agent_respond(item: str, listed_price: float, buyer_offer: float,
                            round_num: int, last_counter: float = None) -> dict:
    if last_counter is None:
        last_counter = listed_price

    # Calculate split in Python — don't trust LLM for math
    split_price = round((buyer_offer + last_counter) / 2, 2)
    # Clamp split to never go above last counter (merchant always comes down)
    split_price = min(split_price, last_counter)

    prompt = f"""You are a merchant agent selling '{item}' listed at ₹{listed_price}.
Buyer's current offer: ₹{buyer_offer}
Your last counter: ₹{last_counter}
Suggested fair counter (split the difference): ₹{split_price}
Round: {round_num} of {MAX_ROUNDS}

Rules:
- Accept if buyer_offer >= ₹{round(listed_price * 0.85)}
- Accept in round 3+ if buyer_offer >= ₹{round(listed_price * 0.75)}
- Counter using the suggested price ₹{split_price} — always LOWER than your last counter
- NEVER counter higher than your last counter ₹{last_counter}
- Reject only if buyer_offer < ₹{round(listed_price * 0.60)}

Respond ONLY with valid JSON, no markdown:
{{"action": "accept"|"counter"|"reject", "price": <number>, "reason": "<short reason>"}}"""

    response = _get_openai_client().chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.choices[0].message.content.strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # LLM returned non-JSON — return a safe reject fallback rather than 500.
        logger.warning("merchant_agent_respond: JSON parse failed, raw=%r", raw)
        return {"action": "reject", "price": last_counter, "reason": "Parse error"}

    # Hard clamp in Python — merchant price must always come DOWN
    if result.get("price") and result["price"] > last_counter:
        result["price"] = split_price
        result["reason"] = f"Clamped: split between buyer {buyer_offer} and last counter {last_counter}"

    return result


def buyer_agent_counter(item: str, listed_price: float, merchant_counter: float,
                        policy_max: float, round_num: int,
                        buyer_last_offer: float = 0.0) -> dict:
    """
    Buyer agent uses Claude to decide next offer within policy limits.
    Returns: { action: "accept"|"counter"|"exit", price: float, reason: str }
    """
    prompt = f"""You are a buyer agent trying to purchase '{item}'.
Listed price: ₹{listed_price}
Merchant's counter offer: ₹{merchant_counter}
Your last offer: ₹{buyer_last_offer}
Your spending policy maximum (HARD LIMIT): ₹{policy_max}
Current round: {round_num} of {MAX_ROUNDS}

Strategy — split the difference every round:
- Your next counter = (your_last_offer + merchant_counter) / 2
- Round that number to nearest integer
- Example: you offered 650, merchant said 764 → your counter = (650+764)/2 = 707
- Example: you offered 707, merchant said 720 → your counter = (707+720)/2 = 713 → ACCEPT since gap is tiny

Rules:
- NEVER counter above merchant_counter — always stay below it
- NEVER exceed policy_max
- Accept if merchant_counter <= policy_max AND gap between your counter and merchant_counter is less than 15
- Accept if round {round_num} == {MAX_ROUNDS} and merchant_counter <= policy_max
- Exit only if merchant_counter > policy_max

Respond ONLY with valid JSON, no markdown:
{{"action": "accept"|"counter"|"exit", "price": <number>, "reason": "<short reason>"}}"""
    
    response = _get_openai_client().chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # LLM returned non-JSON — return a safe exit fallback rather than 500.
        logger.warning("buyer_agent_counter: JSON parse failed, raw=%r", raw)
        return {"action": "exit", "price": buyer_last_offer, "reason": "Parse error"}


def run_negotiation(item: str, listed_price: float, initial_offer: float,
                    credential: dict, daily_spent: float = 0.0) -> dict:
    """
    Full negotiation loop between buyer agent and merchant agent.
    Returns complete session dict with all rounds and final outcome.
    """
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    policy_max = credential["policy"]["max_per_txn"]
    rounds = []
    current_offer = initial_offer
    status = "negotiating"
    final_price = None

    print(f"\n{'='*55}")
    print(f"  Negotiation Session: {session_id}")
    print(f"  Item: {item}  |  Listed: ₹{listed_price}  |  Opening offer: ₹{current_offer}")
    print(f"  Policy max per txn: ₹{policy_max}")
    print(f"{'='*55}")

    last_merchant_counter = listed_price
    for round_num in range(1, MAX_ROUNDS + 1):
        print(f"\n  Round {round_num}:")
        print(f"    Buyer offers: ₹{current_offer:.2f}")

        # Validate against policy before sending offer
        allowed, reason = validate_spend(credential, current_offer, daily_spent)
        if not allowed:
            print(f"    Policy blocked offer: {reason}")
            status = "rejected"
            break

        # Merchant responds
        merchant_resp = merchant_agent_respond(item, listed_price, current_offer, round_num, last_counter=last_merchant_counter)
        print(f"    Merchant {merchant_resp['action']}s at ₹{merchant_resp['price']:.2f}: {merchant_resp['reason']}")
        
        last_merchant_counter = merchant_resp["price"]
        round_data = {
            "round": round_num,
            "buyer_offer": current_offer,
            "merchant_action": merchant_resp["action"],
            "merchant_price": merchant_resp["price"],
            "merchant_reason": merchant_resp["reason"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if merchant_resp["action"] == "accept":
            final_price = current_offer
            status = "settled"
            rounds.append(round_data)
            print(f"\n  ✓ Deal settled at ₹{final_price:.2f}")
            break

        elif merchant_resp["action"] == "reject":
            status = "rejected"
            rounds.append(round_data)
            print(f"\n  ✗ Negotiation rejected by merchant.")
            break

        # Buyer decides next move
        buyer_resp = buyer_agent_counter(
            item, listed_price, merchant_resp["price"],
            policy_max, round_num,
            buyer_last_offer=current_offer
        )
         
        if buyer_resp.get("price") and buyer_resp["price"] > policy_max:
            buyer_resp["price"] = round((current_offer + min(merchant_resp["price"], policy_max)) / 2, 2)
            buyer_resp["action"] = "counter"
            buyer_resp["reason"] = f"Clamped to policy max. Split: ({current_offer} + {min(merchant_resp['price'], policy_max)}) / 2"

        # If merchant price is already under policy max, just accept it
        if merchant_resp["price"] <= policy_max and buyer_resp["action"] == "counter":
            gap = merchant_resp["price"] - current_offer
            if gap < 50:  # gap is small enough, just accept
                buyer_resp["action"] = "accept"
                buyer_resp["price"] = merchant_resp["price"]
                buyer_resp["reason"] = "Gap small enough, accepting merchant price"

        print(f"    Buyer {buyer_resp['action']}s: {buyer_resp['reason']}")
        round_data["buyer_counter_action"] = buyer_resp["action"]
        round_data["buyer_counter_price"] = buyer_resp["price"]
        rounds.append(round_data)

        if buyer_resp["action"] == "accept":
            final_price = merchant_resp["price"]
            status = "settled"
            print(f"\n  ✓ Buyer accepted merchant price ₹{final_price:.2f}")
            break

        elif buyer_resp["action"] == "exit":
            status = "rejected"
            print(f"\n  ✗ Buyer exited negotiation.")
            break

        current_offer = buyer_resp["price"]

    if status == "negotiating":
        status = "rejected"
        print(f"\n  ✗ Max rounds reached, no deal.")

    return {
        "session_id": session_id,
        "item": item,
        "listed_price": listed_price,
        "initial_offer": initial_offer,
        "final_price": final_price,
        "rounds": rounds,
        "status": status,
        "buyer_agent_id": credential["agent_id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    import uuid as _uuid
    from identity import (generate_agent_id, generate_keypair,
                          sign_policy, create_agent_credential)

    # Bootstrap a quick credential for demo
    owner_priv, owner_pub = generate_keypair()
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
    credential = create_agent_credential(agent_id, "user:demo", "pol_demo", policy, sig)

    # Run a negotiation
    session = run_negotiation(
        item="Annual SaaS Subscription",
        listed_price=999.0,
        initial_offer=650.0,
        credential=credential,
        daily_spent=0.0
    )

    print(f"\nFinal session status: {session['status'].upper()}")
    if session['final_price']:
        saved = session['listed_price'] - session['final_price']
        print(f"Saved ₹{saved:.2f} vs listed price!")
