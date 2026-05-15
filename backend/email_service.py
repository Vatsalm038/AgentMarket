import httpx
import logging
import os

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = "deals@signeddeals.in"
BASE_URL = "https://api.resend.com/emails"

logger = logging.getLogger(__name__)


async def _send(to: str, subject: str, html: str) -> None:
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email to %s", to)
        return
    async with httpx.AsyncClient() as client:
        r = await client.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={"from": FROM_EMAIL, "to": [to], "subject": subject, "html": html},
            timeout=10,
        )
        if r.status_code >= 400:
            logger.error("Resend error %s: %s", r.status_code, r.text)


async def send_deal_closed(
    to: str,
    session_id: str,
    amount_inr: float,
    savings_pct: float | None = None,
) -> None:
    savings_line = (
        f"<p>You saved {savings_pct:.1f}% vs your maximum budget.</p>"
        if savings_pct
        else ""
    )
    await _send(
        to,
        "Your deal is confirmed — SignedDeals",
        f"""
    <h2>Deal confirmed</h2>
    <p>Your negotiation session <code>{session_id}</code> closed at <strong>₹{amount_inr:,.2f}</strong>.</p>
    {savings_line}
    <p>Your signed receipt is available in your SignedDeals dashboard.</p>
    """,
    )


async def send_delivery_reminder(
    to: str,
    session_id: str,
    days_remaining: int,
) -> None:
    await _send(
        to,
        f"Delivery reminder — {days_remaining} days remaining",
        f"""
    <h2>Delivery reminder</h2>
    <p>Your order from session <code>{session_id}</code> is expected within <strong>{days_remaining} days</strong>.</p>
    <p>If your order has arrived, please mark it as delivered in your SignedDeals dashboard.</p>
    """,
    )


async def send_delivery_confirmed(to: str, session_id: str) -> None:
    await _send(
        to,
        "Order delivered — SignedDeals",
        f"""
    <h2>Delivery confirmed</h2>
    <p>Your order from session <code>{session_id}</code> has been marked as delivered.</p>
    <p>Thank you for using SignedDeals.</p>
    """,
    )


async def send_dispute_opened(to: str, session_id: str) -> None:
    await _send(
        to,
        "Dispute opened — SignedDeals",
        f"""
    <h2>Dispute notification</h2>
    <p>A dispute has been raised for session <code>{session_id}</code>.</p>
    <p>Our team will review and contact both parties within 48 hours.</p>
    """,
    )
