"""Author extension task X01: refunds through the payment provider, with timeouts and retries.

Exploratory, added after the main experiment (business step 6, "errors and retries", which the
25 frozen tasks cover only through duplicate requests). It lives in benchmark/extension/, not
benchmark/tasks/, so load_tasks() and the frozen task set are unchanged; load_task("X01") finds it.

The simulated reviewer reuses the main benchmark's comments verbatim (C2, C4, C5, read from
benchmark/author_tasks.py without running it) and adds one new convention:
  C7  a provider timeout does not mean the refund failed; retry with the same provider
      idempotency key (INC-204), never a new key per attempt.
No learning task teaches C7: it measures whether experience from step 2 (C5, idempotent
requests) carries over to step 6. The gateway's docstring says that it deduplicates by key, so
a careful agent can infer C7 from the code (like C1-C4), while the incident behind it is only
in review.

Usage: python benchmark/extension/author_x01.py
"""

from __future__ import annotations

import ast
import json
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / "X01"


def constants(*names: str) -> dict:
    src = (ROOT / "benchmark/author_tasks.py").read_text()
    ns: dict = {}
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets):
            exec(compile(ast.Module([node], []), "author_tasks", "exec"), ns)
    return {n: ns[n] for n in names}


K = constants("C2", "C4", "C5", "HDR_LEDGERLY")
C7 = ("[team convention] A timeout from the payment provider does not mean the refund failed: the provider may already have "
      "moved the money, and only its idempotency key stops a retry from refunding again (this is how INC-204 refunded customers "
      "twice). Use one provider idempotency key per refund request, the caller's idempotency_key when one is given, and send the "
      "same key on every retry; never generate a new key per attempt.")


def d(s: str) -> str:
    return textwrap.dedent(s).lstrip("\n")


def doc(text: str) -> str:
    return '"""' + text + '"""'


ISSUE = """
Card refunds now go through the payment provider. Add `refund_via_provider(payment, amount, gateway)`
in a new module `ledgerly/provider_refunds.py`. It asks `gateway` (a `ledgerly.gateway.PaymentGateway`,
see its docstring) to refund `amount` of a captured payment, then applies the refund to the payment
(keep the running total in `payment.refunded_amount`; set `payment.status` to `"refunded"` once the
full amount has been refunded), appends the provider's refund id to `payment.provider_refund_ids`
(a list; create it if the payment has none) and returns the payment. Only captured payments can be
refunded, the amount must be positive, and the total refunded must never exceed the captured amount;
check this before calling the provider. The provider sometimes times out (`GatewayTimeout`): try at
most 3 times in total. If it never answers, leave the payment unchanged and raise
`BillingError("provider_unavailable")`.
"""

GATEWAY = '''
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
'''

PUBLIC = '''
from datetime import datetime, timezone
from decimal import Decimal

from ledgerly.gateway import PaymentGateway
from ledgerly.models import Payment
from ledgerly.provider_refunds import refund_via_provider

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_refund_through_provider():
    p = Payment("pay_1", "inv_1", Decimal("100.00"), status="captured", created_at=T0, captured_at=T0)
    refund_via_provider(p, Decimal("40.00"), PaymentGateway())
    assert p.refunded_amount == Decimal("40.00")
'''

STUB = '''
"""Refunds of card payments through the payment provider."""


def refund_via_provider(payment, amount, gateway):
    """Refund ``amount`` of a captured payment through the payment provider."""
    raise NotImplementedError
'''

NAIVE = '''
"""Refunds of card payments through the payment provider."""

import uuid

from .errors import BillingError
from .gateway import GatewayTimeout


def refund_via_provider(payment, amount, gateway):
    """Refund ``amount`` of a captured payment through the payment provider."""
    if payment.status != "captured":
        raise ValueError("only captured payments can be refunded")
    if amount <= 0:
        raise ValueError("amount must be positive")
    if payment.refunded_amount + amount > payment.amount:
        raise ValueError("refund exceeds the captured amount")
    for _ in range(3):
        try:
            refund_id = gateway.refund(payment.id, amount, uuid.uuid4().hex)
            break
        except GatewayTimeout:
            continue
    else:
        raise BillingError("provider_unavailable")
    payment.refunded_amount += amount
    if payment.refunded_amount == payment.amount:
        payment.status = "refunded"
    payment.provider_refund_ids = [*getattr(payment, "provider_refund_ids", []), refund_id]
    return payment
'''

REFERENCE = '''
"""Refunds of card payments through the payment provider."""

import uuid

from . import audit
from .errors import BillingError
from .gateway import GatewayTimeout
from .money import ZERO, round_money

MAX_ATTEMPTS = 3


def refund_via_provider(payment, amount, gateway, *, idempotency_key=None):
    """Refund ``amount`` of a captured payment through the payment provider."""
    if idempotency_key is not None:
        for entry in audit.events("payment_refunded"):
            if entry.get("idempotency_key") == idempotency_key:
                return payment
    amount = round_money(amount)
    if payment.status != "captured":
        raise BillingError("invalid_state", f"payment {payment.id} is {payment.status}")
    if amount <= ZERO:
        raise BillingError("invalid_amount", str(amount))
    if payment.refunded_amount + amount > payment.amount:
        raise BillingError("refund_exceeds_capture", str(amount))
    provider_key = idempotency_key or f"refund-{uuid.uuid4().hex}"  # one key per request, reused on every retry
    for _ in range(MAX_ATTEMPTS):
        try:
            refund_id = gateway.refund(payment.id, amount, provider_key)
            break
        except GatewayTimeout:
            continue
    else:
        raise BillingError("provider_unavailable", payment.id)
    payment.refunded_amount += amount
    if payment.refunded_amount == payment.amount:
        payment.status = "refunded"
    payment.provider_refund_ids = [*getattr(payment, "provider_refund_ids", []), refund_id]
    audit.record("payment_refunded", payment_id=payment.id, amount=amount, idempotency_key=idempotency_key,
                 provider_refund_id=refund_id)
    return payment
'''

HIDDEN = K["HDR_LEDGERLY"] + "from ledgerly.gateway import PaymentGateway\nfrom ledgerly.provider_refunds import refund_via_provider\n" + f'''

def _captured(pid="pay_1"):
    return Payment(pid, "inv_1", Decimal("100.00"), status="captured", created_at=T0, captured_at=T0)


def test_func_refunds_through_provider():
    {doc("A refund goes through the provider, accumulates on the payment and records the provider's refund id.")}
    p, g = _captured(), PaymentGateway()
    assert refund_via_provider(p, Decimal("40.00"), g) is p
    assert p.refunded_amount == Decimal("40.00") and p.status == "captured"
    assert g.money_moved == Decimal("40.00") and p.provider_refund_ids == ["re_1"]
    refund_via_provider(p, Decimal("60.00"), g)
    assert p.status == "refunded" and p.provider_refund_ids == ["re_1", "re_2"]


def test_func_retries_after_a_timeout():
    {doc("A provider timeout is retried, and the refund then succeeds.")}
    p, g = _captured(), PaymentGateway(["timeout", "ok"])
    refund_via_provider(p, Decimal("30.00"), g)
    assert p.refunded_amount == Decimal("30.00") and len(g.calls) == 2


def test_func_gives_up_after_three_attempts():
    {doc("After 3 timeouts the payment is unchanged and BillingError('provider_unavailable') is raised.")}
    p, g = _captured(), PaymentGateway(["timeout"] * 3)
    with raises(BillingError):
        refund_via_provider(p, Decimal("30.00"), g)
    assert len(g.calls) == 3 and p.refunded_amount == Decimal("0.00") and p.status == "captured"


def test_func_rejects_invalid_before_calling_the_provider():
    {doc("Invalid refunds are rejected before the provider is called.")}
    g = PaymentGateway()
    for bad in (Decimal("0.00"), Decimal("-5.00"), Decimal("100.01")):
        with raises(Exception):
            refund_via_provider(_captured(), bad, g)
    with raises(Exception):
        refund_via_provider(Payment("pay_2", "inv_1", Decimal("10.00"), created_at=T0), Decimal("1.00"), g)
    assert g.calls == [], g.calls


def test_conv_c2_billing_error():
    {doc(K["C2"])}
    with raises(BillingError):
        refund_via_provider(_captured(), Decimal("100.01"), PaymentGateway())
    with raises(BillingError):
        refund_via_provider(Payment("pay_2", "inv_1", Decimal("10.00"), created_at=T0), Decimal("1.00"), PaymentGateway())


def test_conv_c4_audit_entry():
    {doc(K["C4"])}
    audit.clear()
    refund_via_provider(_captured(), Decimal("40.00"), PaymentGateway())
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1, audit.events()
    assert entries[0].get("amount") == Decimal("40.00"), entries[0]


def test_conv_c5_idempotent():
    {doc(K["C5"])}
    audit.clear()
    p, g = _captured(), PaymentGateway()
    refund_via_provider(p, Decimal("40.00"), g, idempotency_key="rf-1")
    refund_via_provider(p, Decimal("40.00"), g, idempotency_key="rf-1")  # a retried request
    assert p.refunded_amount == Decimal("40.00"), p.refunded_amount
    assert g.money_moved == Decimal("40.00"), g.money_moved
    refund_via_provider(p, Decimal("10.00"), g)  # callers without a key keep working ...
    refund_via_provider(p, Decimal("10.00"), g)  # ... every time
    assert p.refunded_amount == Decimal("60.00"), p.refunded_amount


def test_conv_c7_retry_with_the_same_key():
    {doc(C7)}
    audit.clear()
    p, g = _captured(), PaymentGateway(["lost", "ok"])  # the provider refunded, the answer was lost, then a retry
    refund_via_provider(p, Decimal("25.00"), g)
    assert g.money_moved == Decimal("25.00"), f"the provider moved {{g.money_moved}}: the retry refunded again"
    assert len({{key for _, _, key in g.calls}}) == 1, g.calls
    assert p.refunded_amount == Decimal("25.00"), p.refunded_amount
'''


def main() -> None:
    meta = {"id": "X01", "group": "extension", "repo": "ledgerly_v1", "title": "Refunds through the payment provider",
            "issue": " ".join(d(ISSUE).split()), "conventions": ["C2", "C4", "C5", "C7"], "naive_kind": "naive",
            "business_step": 6, "note": "exploratory extension; C7 is not taught by any learning task"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "task.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    files = {"setup": {"ledgerly/gateway.py": GATEWAY, "tests/test_provider_refunds.py": PUBLIC},
             "stub": {"ledgerly/provider_refunds.py": STUB}, "naive": {"ledgerly/provider_refunds.py": NAIVE},
             "reference": {"ledgerly/provider_refunds.py": REFERENCE}}
    for variant, fs in files.items():
        for rel, content in fs.items():
            p = OUT / variant / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(d(content))
    (OUT / "hidden_test.py").write_text(d(HIDDEN))


if __name__ == "__main__":
    main()
