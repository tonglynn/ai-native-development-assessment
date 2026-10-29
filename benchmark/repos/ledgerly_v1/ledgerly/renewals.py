"""Renewal reminders (moved over from the old billing monolith)."""

from datetime import datetime, timedelta

REMINDER_DAYS_BEFORE = 3


def reminder_due(renewal_at: datetime, now: datetime | None = None) -> bool:
    now = now or datetime.now()
    return renewal_at - timedelta(days=REMINDER_DAYS_BEFORE) <= now < renewal_at
