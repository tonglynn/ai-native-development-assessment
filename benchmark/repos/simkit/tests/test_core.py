import pytest

from simkit.integrate import trapezoid
from simkit.stats import mean, rms
from simkit.units import seconds_to_hours, watts_to_kw


def test_trapezoid():
    assert trapezoid([0.0, 1.0, 2.0], [0.0, 1.0, 0.0]) == pytest.approx(1.0)


def test_trapezoid_length_mismatch():
    with pytest.raises(ValueError):
        trapezoid([0.0, 1.0], [1.0])


def test_units():
    assert watts_to_kw(1500.0) == pytest.approx(1.5)
    assert seconds_to_hours(5400.0) == pytest.approx(1.5)


def test_stats():
    assert mean([1.0, 2.0, 3.0]) == pytest.approx(2.0)
    assert rms([3.0, 4.0]) == pytest.approx(12.5 ** 0.5)
