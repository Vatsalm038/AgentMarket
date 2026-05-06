"""
Module: Daily Spend Tracker
Calculates how much an agent has spent today from the audit log.
Used by negotiate endpoint before allowing any new transaction.
"""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models import AuditLog
import json


async def get_daily_spent(agent_id: str, db: AsyncSession) -> float:
    """
    Sum all settled transaction amounts for an agent today (UTC).
    Reads from audit_log where event = 'payment_settled'.
    """
    today_start = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    result = await db.execute(
        select(AuditLog).where(
            AuditLog.agent_id == agent_id,
            AuditLog.event == "payment_settled",
            AuditLog.timestamp >= today_start
        )
    )
    logs = result.scalars().all()

    total = 0.0
    for log in logs:
        try:
            payload = json.loads(log.payload)
            total += float(payload.get("amount", 0))
        except Exception:
            pass

    return total


async def get_spend_summary(agent_id: str, db: AsyncSession) -> dict:
    """
    Returns a full spend summary for an agent:
    - today's spend
    - total all-time spend
    - number of settled transactions
    """
    today_start = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    result = await db.execute(
        select(AuditLog).where(
            AuditLog.agent_id == agent_id,
            AuditLog.event == "payment_settled"
        )
    )
    all_logs = result.scalars().all()

    today_total = 0.0
    all_time_total = 0.0
    count = 0

    for log in all_logs:
        try:
            payload = json.loads(log.payload)
            amount = float(payload.get("amount", 0))
            all_time_total += amount
            count += 1
            if log.timestamp >= today_start:
                today_total += amount
        except Exception:
            pass

    return {
        "agent_id": agent_id,
        "today_spent": today_total,
        "all_time_spent": all_time_total,
        "total_transactions": count,
        "date": today_start.date().isoformat()
    }
