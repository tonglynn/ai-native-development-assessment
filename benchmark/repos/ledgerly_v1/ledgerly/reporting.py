"""Finance dashboard queries (moved over from the old billing monolith)."""

from datetime import date, datetime, time, timedelta


def day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min)
    return start, start + timedelta(days=1)


def total_amount(payments) -> float:
    return round(sum(float(p.amount) for p in payments), 2)
