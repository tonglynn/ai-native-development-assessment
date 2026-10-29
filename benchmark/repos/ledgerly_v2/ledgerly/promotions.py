"""Promotion campaigns (moved over from the old billing monolith)."""

from datetime import datetime

CAMPAIGNS = {"black-friday": {"percent": 30, "ends": datetime(2025, 12, 1)}}


def campaign_percent(name: str, now: datetime | None = None) -> int:
    campaign = CAMPAIGNS.get(name)
    if campaign is None:
        raise ValueError(f"unknown campaign {name!r}")
    now = now or datetime.now()
    return campaign["percent"] if now < campaign["ends"] else 0


def bulk_discount_percent(quantity: int) -> int:
    if quantity < 0:
        raise ValueError("quantity must be non-negative")
    if quantity >= 50:
        return 10
    return 5 if quantity >= 10 else 0
