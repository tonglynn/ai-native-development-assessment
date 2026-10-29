def trapezoid(xs: list[float], ys: list[float]) -> float:
    """Integrate sampled points with the trapezoidal rule."""
    if len(xs) != len(ys):
        raise ValueError("xs and ys must have the same length")
    if len(xs) < 2:
        raise ValueError("need at least two samples")
    total = 0.0
    for i in range(1, len(xs)):
        total += (xs[i] - xs[i - 1]) * (ys[i] + ys[i - 1]) / 2.0
    return total
