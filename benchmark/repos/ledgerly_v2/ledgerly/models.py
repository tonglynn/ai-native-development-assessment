from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class LineItem:
    description: str
    quantity: int
    unit_price: Decimal


@dataclass
class Invoice:
    id: str
    customer_id: str
    currency: str = "USD"
    lines: list[LineItem] = field(default_factory=list)
    issued_at: datetime | None = None
    status: str = "draft"  # draft | issued | paid | void


@dataclass
class Payment:
    id: str
    invoice_id: str
    amount: Decimal
    status: str = "authorized"  # authorized | captured | voided | refunded
    created_at: datetime | None = None
    captured_at: datetime | None = None
    refunded_amount: Decimal = Decimal("0.00")


@dataclass
class Subscription:
    id: str
    customer_id: str
    plan_price: Decimal
    period_days: int
    started_at: datetime
    canceled_at: datetime | None = None
