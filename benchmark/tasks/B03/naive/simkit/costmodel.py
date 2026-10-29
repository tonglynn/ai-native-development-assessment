from decimal import ROUND_HALF_UP, Decimal


class CostError(Exception):
    pass


def cost_per_sample(total_cost, samples):
    if samples <= 0:
        raise CostError("invalid_samples")
    return (Decimal(str(total_cost)) / samples).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
