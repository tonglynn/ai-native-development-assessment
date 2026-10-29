SECONDS_PER_HOUR = 3600.0


def watts_to_kw(watts: float) -> float:
    return watts / 1000.0


def seconds_to_hours(seconds: float) -> float:
    if seconds < 0:
        raise ValueError("seconds must be non-negative")
    return seconds / SECONDS_PER_HOUR
