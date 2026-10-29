def cost_per_sample(total_cost: float, samples: int) -> float:
    """Total cost split evenly across samples, 4 decimals."""
    if samples <= 0:
        raise ValueError("samples must be positive")
    return round(total_cost / samples, 4)
