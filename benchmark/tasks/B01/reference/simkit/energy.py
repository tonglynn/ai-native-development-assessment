from .units import watts_to_kw


def energy_cost(power_watts: float, hours: float, price_per_kwh: float) -> float:
    """Cost of running a load, rounded to 2 decimals."""
    if power_watts < 0 or hours < 0 or price_per_kwh < 0:
        raise ValueError("inputs must be non-negative")
    return round(watts_to_kw(power_watts) * hours * price_per_kwh, 2)
