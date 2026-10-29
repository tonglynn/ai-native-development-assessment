import pytest

from simkit.costmodel import cost_per_sample


def test_cost_per_sample():
    assert cost_per_sample(10.0, 4) == pytest.approx(2.5)
