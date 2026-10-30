"""Optional relevance check of the applied line (D37)."""

from attest.memory.evidence import applied_is_relevant, code_names


def test_relevance():
    quote = "Write the amount in audit entries as float(amount)"
    assert code_names(quote) == {"float"}
    assert applied_is_relevant(quote, "amount=float(amount),") is True
    assert applied_is_relevant(quote, 'audit.record("payment_refunded", payment_id=payment.id, amount=amount)') is False
    assert applied_is_relevant("Round money only with ledgerly.money.round_money", "return round_money(total)") is True
    assert applied_is_relevant("Datetimes must be timezone-aware UTC", "at = ensure_utc(at)") is None  # names no code
