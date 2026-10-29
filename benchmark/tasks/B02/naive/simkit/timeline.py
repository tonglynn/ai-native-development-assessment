from datetime import datetime, timedelta, timezone


def sample_times(start, step, count):
    if step <= 0 or count < 0:
        raise ValueError("step must be positive and count non-negative")
    base = datetime.fromtimestamp(start, tz=timezone.utc)
    return [base + timedelta(seconds=step * i) for i in range(count)]
