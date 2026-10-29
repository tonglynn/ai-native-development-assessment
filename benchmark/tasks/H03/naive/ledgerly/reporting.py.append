def payments_between(payments, start, end):
    selected = [p for p in payments if start <= p.created_at < end]
    return sorted(selected, key=lambda p: p.created_at)
