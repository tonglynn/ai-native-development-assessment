from datetime import datetime

from .clock import ensure_utc
from .errors import BillingError
from .models import Payment


def payments_between(payments: list[Payment], start: datetime, end: datetime) -> list[Payment]:
    """Payments created in [start, end), oldest first."""
    start, end = ensure_utc(start), ensure_utc(end)
    if end < start:
        raise BillingError("invalid_window", f"{start.isoformat()} > {end.isoformat()}")
    selected = [p for p in payments if start <= ensure_utc(p.created_at) < end]
    return sorted(selected, key=lambda p: p.created_at)
