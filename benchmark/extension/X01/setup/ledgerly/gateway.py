"""Client for the payment provider's refund API (a test double in this repository).

``PaymentGateway.refund(payment_id, amount, idempotency_key)`` asks the provider to refund
``amount`` and returns the provider's refund id. The provider deduplicates by
``idempotency_key``: a call with a key it has already seen returns the first refund id and
moves no money. A call can raise ``GatewayTimeout``: the provider did not answer in time,
which does not tell you whether it refunded.
"""

from decimal import Decimal


class GatewayTimeout(Exception):
    """The provider did not answer in time."""


class PaymentGateway:
    def __init__(self, script=()):
        # Test hook: one outcome per call, "ok" (default), "timeout" (nothing happened) or
        # "lost" (the provider refunded, but the answer never arrived).
        self._script = list(script)
        self.calls = []
        self.refunds = {}  # idempotency key -> (refund id, amount)

    def refund(self, payment_id, amount, idempotency_key):
        self.calls.append((payment_id, amount, idempotency_key))
        outcome = self._script.pop(0) if self._script else "ok"
        if outcome == "timeout":
            raise GatewayTimeout(payment_id)
        if idempotency_key not in self.refunds:
            self.refunds[idempotency_key] = (f"re_{len(self.refunds) + 1}", Decimal(amount))
        if outcome == "lost":
            raise GatewayTimeout(payment_id)
        return self.refunds[idempotency_key][0]

    @property
    def money_moved(self):
        return sum((a for _, a in self.refunds.values()), Decimal("0.00"))
