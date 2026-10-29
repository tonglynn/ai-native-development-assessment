def sample_times(start: float, step: float, count: int) -> list[float]:
    """Evenly spaced sample timestamps."""
    if step <= 0:
        raise ValueError("step must be positive")
    if count < 0:
        raise ValueError("count must be non-negative")
    return [start + i * step for i in range(count)]
