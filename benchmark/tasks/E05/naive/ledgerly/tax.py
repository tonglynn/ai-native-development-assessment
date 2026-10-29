def add_tax(amount, rate_percent):
    rate = float(rate_percent)
    if rate < 0 or rate > 100:
        raise ValueError("tax rate must be between 0 and 100")
    return round(float(amount) * (1 + rate / 100), 2)
