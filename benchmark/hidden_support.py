"""Helpers available to hidden tests (copied next to them at verification time)."""

import contextlib


@contextlib.contextmanager
def raises(exc_type):
    """Like pytest.raises, but reports which exception type was raised instead."""
    try:
        yield
    except exc_type:
        return
    except Exception as exc:  # noqa: BLE001 - we want to report any other type
        raise AssertionError(f"expected {exc_type.__name__}, got {type(exc).__name__}: {exc}") from None
    raise AssertionError(f"expected {exc_type.__name__} to be raised, but nothing was raised")


def close(a, b, tol=1e-9):
    return abs(float(a) - float(b)) <= tol
