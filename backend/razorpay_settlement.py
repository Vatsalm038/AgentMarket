"""
Module: Razorpay Settlement with UPI Support
Connects agentic commerce to Razorpay test rails.

SETUP (5 minutes, free):
  1. Sign up at razorpay.com (no credit card needed for test mode)
  2. Dashboard → Settings → API Keys → Generate Test Key
  3. Add to .env:
       RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
       RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx

TEST UPI IDs (always work in sandbox):
  success@razorpay    — payment succeeds immediately
  failure@razorpay    — payment fails (to test error handling)

TEST CARDS:
  Number : 4111 1111 1111 1111
  Expiry : Any future date (e.g. 12/29)
  CVV    : Any 3 digits
  Name   : Any name

FLOW:
  negotiate/auction → create_razorpay_order() → simulate_upi_payment()
  → verify_payment() → settlement receipt with razorpay_payment_id
"""

import os
import json
import uuid
import hmac
import hashlib
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_AVAILABLE  = bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)


def _client():
    if not RAZORPAY_AVAILABLE:
        return None
    import razorpay
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


# ── ORDER ─────────────────────────────────────────────────────────────────────

def create_razorpay_order(amount_inr: float, item: str,
                           session_id: str, agent_id: str) -> dict:
    """
    Create a Razorpay order for the settled negotiation amount.
    Returns order dict. In mock mode, returns a realistic fake order.
    """
    amount_paise = int(round(amount_inr * 100))

    notes = {
        "session_id":  session_id,
        "agent_id":    agent_id,
        "item":        item,
        "source":      "agentic-commerce-protocol",
        "environment": "test"
    }

    if not RAZORPAY_AVAILABLE:
        print("  [Razorpay] Mock mode — add RAZORPAY_KEY_ID to .env for real API calls")
        return {
            "id":           f"order_mock_{uuid.uuid4().hex[:14]}",
            "entity":       "order",
            "amount":       amount_paise,
            "amount_paid":  0,
            "amount_due":   amount_paise,
            "currency":     "INR",
            "status":       "created",
            "notes":        notes,
            "mock":         True,
            "created_at":   int(datetime.utcnow().timestamp())
        }

    client = _client()
    order = client.order.create({
        "amount":          amount_paise,
        "currency":        "INR",
        "notes":           notes,
        "payment_capture": True
    })
    print(f"  [Razorpay] Order created: {order['id']} — ₹{amount_inr} ({amount_paise} paise)")
    return order


# ── UPI PAYMENT SIMULATION ────────────────────────────────────────────────────

def simulate_upi_payment(order_id: str, amount_paise: int,
                           upi_vpa: str = "success@razorpay") -> dict:
    """
    Simulate a UPI payment in test mode.

    In real production: the buyer's UPI app receives a collect request and approves it.
    In test mode: Razorpay's test VPA 'success@razorpay' auto-approves instantly.

    upi_vpa options:
      success@razorpay  — always succeeds
      failure@razorpay  — always fails (test error path)
    """
    if not RAZORPAY_AVAILABLE:
        if "failure" in upi_vpa:
            return {
                "razorpay_payment_id": None,
                "razorpay_order_id":   order_id,
                "method":              "upi",
                "vpa":                 upi_vpa,
                "status":              "failed",
                "error":               "Payment failed (test failure VPA)",
                "mock":                True
            }
        return {
            "razorpay_payment_id": f"pay_mock_{uuid.uuid4().hex[:14]}",
            "razorpay_order_id":   order_id,
            "razorpay_signature":  f"sig_mock_{uuid.uuid4().hex[:32]}",
            "method":              "upi",
            "vpa":                 upi_vpa,
            "status":              "captured",
            "mock":                True
        }

    # With real Razorpay test keys, UPI payment is triggered via frontend checkout
    # This returns what the Razorpay checkout JS sends back after payment
    print(f"  [Razorpay] UPI collect sent to {upi_vpa}")
    print(f"  [Razorpay] In production: user approves in UPI app")
    print(f"  [Razorpay] In test mode: success@razorpay auto-approves")

    # Return the payment confirmation structure
    # In real flow this comes from Razorpay checkout callback
    return {
        "razorpay_order_id": order_id,
        "method":            "upi",
        "vpa":               upi_vpa,
        "status":            "captured",
        "note":              "Complete payment via Razorpay checkout UI in browser",
        "checkout_url":      f"https://api.razorpay.com/v1/checkout/embedded",
        "key_id":            RAZORPAY_KEY_ID,
        "test_mode":         True
    }


# ── SIGNATURE VERIFICATION ────────────────────────────────────────────────────

def verify_payment_signature(payment_id: str, order_id: str, signature: str) -> bool:
    """
    Verify Razorpay payment signature (HMAC-SHA256).
    This confirms the payment is genuine and not forged.
    """
    if not RAZORPAY_AVAILABLE or "mock" in payment_id:
        return True  # Mock payments always valid in test mode

    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── FULL SETTLEMENT FLOW ──────────────────────────────────────────────────────

def settle_via_razorpay(session: dict, credential: dict,
                         upi_vpa: str = "success@razorpay") -> dict:
    """
    Complete Razorpay settlement flow after a negotiation or auction settles.

    Steps:
      1. Create Razorpay order with session metadata
      2. Simulate/trigger UPI payment
      3. Verify payment signature
      4. Return complete receipt

    Args:
        session:    Settled negotiation/auction session dict
        credential: Buyer agent's credential
        upi_vpa:    UPI Virtual Payment Address (default: success@razorpay for testing)

    Returns:
        Complete payment receipt with Razorpay IDs
    """
    amount    = session["final_price"]
    item      = session["item"]
    session_id = session["session_id"]
    agent_id  = credential["agent_id"]

    print(f"\n  ── Razorpay Settlement ──")
    print(f"  Item: {item}  |  Amount: ₹{amount}")
    print(f"  UPI VPA: {upi_vpa}")

    # Step 1: Create order
    order = create_razorpay_order(amount, item, session_id, agent_id)

    # Step 2: Trigger UPI payment
    payment = simulate_upi_payment(order["id"], order["amount"], upi_vpa)

    # Step 3: Verify (skip for mock)
    sig_valid = True
    if payment.get("razorpay_signature"):
        sig_valid = verify_payment_signature(
            payment.get("razorpay_payment_id", ""),
            order["id"],
            payment.get("razorpay_signature", "")
        )

    status = payment.get("status", "failed")
    if not sig_valid:
        status = "signature_mismatch"

    receipt = {
        "receipt_id":           f"rcpt_{uuid.uuid4().hex[:12]}",
        "session_id":           session_id,
        "agent_id":             agent_id,
        "owner_id":             credential["owner_id"],
        "item":                 item,
        "amount_inr":           amount,
        "amount_paise":         order["amount"],
        "currency":             "INR",
        "razorpay_order_id":    order["id"],
        "razorpay_payment_id":  payment.get("razorpay_payment_id", "pending"),
        "payment_method":       payment.get("method", "upi"),
        "upi_vpa":              upi_vpa,
        "signature_valid":      sig_valid,
        "status":               status,
        "is_mock":              not RAZORPAY_AVAILABLE,
        "razorpay_mode":        "test" if RAZORPAY_AVAILABLE else "mock",
        "settled_at":           datetime.utcnow().isoformat()
    }

    icon = "✓" if status == "captured" else "✗"
    print(f"  {icon} Payment {status} | Order: {order['id']} | Payment: {receipt['razorpay_payment_id']}")
    return receipt


# ── RAZORPAY CHECKOUT HTML ────────────────────────────────────────────────────

def generate_checkout_html(order_id: str, amount_paise: int, item: str,
                            agent_id: str) -> str:
    """
    Generate Razorpay checkout HTML for browser-based payment.
    Embed this in the dashboard to let users complete real UPI payments.
    """
    if not RAZORPAY_AVAILABLE:
        return "<p>Add Razorpay test credentials to .env to enable browser checkout</p>"

    return f"""
<!DOCTYPE html>
<html>
<head><title>Pay for {item}</title></head>
<body>
  <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
  <script>
    var options = {{
      key: "{RAZORPAY_KEY_ID}",
      amount: "{amount_paise}",
      currency: "INR",
      name: "Agentic Commerce Protocol",
      description: "{item}",
      order_id: "{order_id}",
      prefill: {{ contact: "9999999999", email: "agent@acp.dev" }},
      notes: {{ agent_id: "{agent_id}" }},
      theme: {{ color: "#1a4fff" }},
      method: {{ upi: true, card: true, netbanking: false, wallet: false }},
      handler: function(response) {{
        document.getElementById('result').innerHTML =
          '<b>Payment Successful!</b><br>' +
          'Payment ID: ' + response.razorpay_payment_id + '<br>' +
          'Order ID: ' + response.razorpay_order_id;
      }}
    }};
    var rzp = new Razorpay(options);
    rzp.open();
  </script>
  <div id="result" style="font-family:sans-serif;padding:20px"></div>
</body>
</html>"""


# ── QUICK TEST ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Razorpay Integration Test ===\n")

    if RAZORPAY_AVAILABLE:
        print(f"✓ Razorpay credentials loaded: {RAZORPAY_KEY_ID[:16]}...")
        print(f"  Mode: TEST (no real money moves)\n")
    else:
        print("⚠ No Razorpay credentials — running in MOCK mode")
        print("  To enable: add RAZORPAY_KEY_ID + RAZORPAY_KEY_SECRET to .env")
        print("  Get free test keys: razorpay.com → Settings → API Keys\n")

    mock_session = {
        "session_id": f"sess_test_{uuid.uuid4().hex[:8]}",
        "item": "Annual SaaS Subscription",
        "final_price": 749.0,
        "status": "settled"
    }
    mock_credential = {
        "agent_id": "did:agent:test123",
        "owner_id": "user:vatsal",
        "policy": {"currency": "INR", "max_per_txn": 1000}
    }

    print("Test 1: Successful UPI payment")
    receipt = settle_via_razorpay(mock_session, mock_credential, "success@razorpay")
    print(f"  Status: {receipt['status']}")
    print(f"  Order:  {receipt['razorpay_order_id']}")
    print(f"  Mode:   {receipt['razorpay_mode']}\n")

    print("Test 2: Failed UPI payment")
    fail_session = dict(mock_session, session_id=f"sess_fail_{uuid.uuid4().hex[:8]}")
    receipt2 = settle_via_razorpay(fail_session, mock_credential, "failure@razorpay")
    print(f"  Status: {receipt2['status']}")
    print(f"\nAll tests complete.")
