"""
Module: Multi-Merchant Auction
Multiple merchant agents compete simultaneously for a buyer's order.
Buyer agent (GPT-4o-mini powered) picks the best deal after all merchants respond.
"""

import os
import json
import uuid
from datetime import datetime
from openai import OpenAI
from identity import validate_spend

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def merchant_initial_quote(merchant_id: str, merchant_name: str,
                            item: str, listed_price: float, buyer_budget: float) -> dict:
    min_price = round(listed_price * 0.70, 2)
    max_price = round(listed_price * 0.98, 2)

    prompt = f"""You are merchant agent '{merchant_name}' competing in an auction to sell '{item}'.
Listed price: ₹{listed_price}. Buyer budget: ₹{buyer_budget}.
You are competing with other merchants — bid competitively to win.
Your quote MUST be between ₹{min_price} and ₹{max_price}.

Respond ONLY with valid JSON, no markdown:
{{"merchant_id": "{merchant_id}", "merchant_name": "{merchant_name}", "quote": <number between {min_price} and {max_price}>, "pitch": "<one sentence why buyer should choose you>"}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini", max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    result = json.loads(response.choices[0].message.content.strip())
    result["quote"] = round(max(min_price, min(float(result["quote"]), min(max_price, buyer_budget))), 2)
    return result


def buyer_evaluate_quotes(item: str, quotes: list[dict],
                           policy_max: float, buyer_priorities: str = "lowest price") -> dict:
    valid = [q for q in quotes if q["quote"] <= policy_max]
    if not valid:
        valid = sorted(quotes, key=lambda x: x["quote"])[:1]

    quotes_text = "\n".join([
        f"- {q['merchant_name']}: ₹{q['quote']} — {q['pitch']}" for q in valid
    ])

    prompt = f"""You are a buyer agent selecting the best deal for '{item}'.
Policy max: ₹{policy_max}. Priorities: {buyer_priorities}.

Valid quotes:
{quotes_text}

Pick the best option based on price and pitch quality.
Respond ONLY with valid JSON, no markdown:
{{"winner_merchant_id": "<id>", "winner_merchant_name": "<n>", "reason": "<why>", "final_price": <number>}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini", max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    result = json.loads(response.choices[0].message.content.strip())
    result["final_price"] = min(float(result["final_price"]), policy_max)

    winner_quote = next((q for q in valid if q["merchant_name"] == result["winner_merchant_name"]), None)
    if not winner_quote:
        winner_quote = sorted(valid, key=lambda x: x["quote"])[0]
        result["winner_merchant_name"] = winner_quote["merchant_name"]
        result["winner_merchant_id"] = winner_quote["merchant_id"]
        result["final_price"] = winner_quote["quote"]

    return result


def run_auction(item: str, listed_price: float, credential: dict,
                num_merchants: int = 3, buyer_priorities: str = "lowest price") -> dict:
    auction_id = f"auction_{uuid.uuid4().hex[:12]}"
    policy_max = credential["policy"]["max_per_txn"]
    buyer_agent_id = credential["agent_id"]

    merchant_names = [
        "QuickCommerce Pro", "ValueMart Agent", "PrimeDeal Bot",
        "SwiftSell AI", "BargainBot X", "TradeAgent One"
    ]
    merchants = [
        {"id": f"did:agent:merchant_{uuid.uuid4().hex[:8]}", "name": merchant_names[i % len(merchant_names)]}
        for i in range(max(2, min(num_merchants, 6)))
    ]

    print(f"\n{'='*60}")
    print(f"  AUCTION: {auction_id}")
    print(f"  Item: {item}  |  Listed: ₹{listed_price}  |  Budget: ₹{policy_max}")
    print(f"  {len(merchants)} merchants competing")
    print(f"{'='*60}")

    print(f"\n  Phase 1: Collecting quotes...")
    quotes = []
    for merchant in merchants:
        try:
            quote = merchant_initial_quote(merchant["id"], merchant["name"], item, listed_price, policy_max)
            quotes.append(quote)
            print(f"  [{merchant['name']}] ₹{quote['quote']:.2f} — {quote['pitch']}")
        except Exception as e:
            print(f"  [{merchant['name']}] Failed: {e}")

    if not quotes:
        return {"auction_id": auction_id, "status": "failed", "reason": "No merchants responded",
                "all_quotes": [], "winner": None, "buyer_agent_id": buyer_agent_id,
                "created_at": datetime.utcnow().isoformat()}

    valid_quotes = [q for q in quotes if q["quote"] <= policy_max]
    if not valid_quotes:
        return {"auction_id": auction_id, "status": "failed",
                "reason": f"All quotes exceeded policy max ₹{policy_max}",
                "all_quotes": quotes, "valid_quotes_count": 0, "winner": None,
                "buyer_agent_id": buyer_agent_id, "created_at": datetime.utcnow().isoformat()}

    print(f"\n  Phase 2: Buyer evaluating {len(valid_quotes)} valid quotes...")
    winner = buyer_evaluate_quotes(item, valid_quotes, policy_max, buyer_priorities)
    print(f"\n  Winner: {winner['winner_merchant_name']} at ₹{winner['final_price']:.2f}")
    print(f"  Reason: {winner['reason']}")

    allowed, reason = validate_spend(credential, winner["final_price"])
    if not allowed:
        return {"auction_id": auction_id, "status": "policy_blocked", "reason": reason,
                "all_quotes": quotes, "winner": winner, "buyer_agent_id": buyer_agent_id,
                "created_at": datetime.utcnow().isoformat()}

    saved_vs_listed = round(listed_price - winner["final_price"], 2)
    saved_vs_highest = round(max(q["quote"] for q in valid_quotes) - winner["final_price"], 2)

    return {
        "auction_id": auction_id, "status": "settled", "item": item,
        "listed_price": listed_price, "all_quotes": quotes,
        "valid_quotes_count": len(valid_quotes), "winner": winner,
        "final_price": winner["final_price"], "buyer_agent_id": buyer_agent_id,
        "savings_vs_listed": saved_vs_listed,
        "savings_vs_highest_quote": saved_vs_highest,
        "buyer_priorities": buyer_priorities,
        "merchants_competed": len(merchants),
        "created_at": datetime.utcnow().isoformat()
    }
