import math


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("mean of empty sequence")
    return math.fsum(values) / len(values)


def rms(values: list[float]) -> float:
    if not values:
        raise ValueError("rms of empty sequence")
    return math.sqrt(math.fsum(v * v for v in values) / len(values))
