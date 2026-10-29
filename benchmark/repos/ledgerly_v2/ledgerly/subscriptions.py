from datetime import datetime, timedelta

from .clock import ensure_utc
from .errors import BillingError
from .models import Subscription


def current_period(sub: Subscription, at: datetime) -> tuple[datetime, datetime]:
    """Return the [start, end) billing period of ``sub`` that contains ``at``."""
    at = ensure_utc(at)
    start = ensure_utc(sub.started_at)
    if at < start:
        raise BillingError("before_start", at.isoformat())
    length = timedelta(days=sub.period_days)
    n = (at - start) // length
    period_start = start + n * length
    return period_start, period_start + length
