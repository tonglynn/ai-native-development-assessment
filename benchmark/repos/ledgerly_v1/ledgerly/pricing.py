"""Plan prices and coupons (moved over from the old billing monolith)."""

PLAN_PRICES = {"starter": 9.99, "team": 49.0, "business": 199.0}
COUPONS = {"WELCOME10": 10, "PARTNER25": 25}


def list_price(plan_code: str) -> float:
    try:
        return PLAN_PRICES[plan_code]
    except KeyError:
        raise ValueError(f"unknown plan {plan_code!r}") from None


def apply_coupon(price: float, coupon: str) -> float:
    if coupon not in COUPONS:
        raise ValueError(f"unknown coupon {coupon!r}")
    return round(price * (100 - COUPONS[coupon]) / 100, 2)
