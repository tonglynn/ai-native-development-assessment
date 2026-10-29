from datetime import datetime, timezone

from .errors import BillingError


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime) -> datetime:
    if not isinstance(dt, datetime):
        raise BillingError("invalid_datetime", repr(dt))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise BillingError("naive_datetime", dt.isoformat())
    return dt.astimezone(timezone.utc)
