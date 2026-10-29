from decimal import ROUND_HALF_UP, Decimal


class SimulationError(Exception):
    pass


def energy_cost(power_watts, hours, price_per_kwh):
    if power_watts < 0 or hours < 0 or price_per_kwh < 0:
        raise SimulationError("negative_input")
    cost = Decimal(str(power_watts)) / 1000 * Decimal(str(hours)) * Decimal(str(price_per_kwh))
    return cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
