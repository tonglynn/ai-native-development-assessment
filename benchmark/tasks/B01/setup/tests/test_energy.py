import pytest

from simkit.energy import energy_cost


def test_energy_cost():
    assert energy_cost(1500.0, 2.0, 0.25) == pytest.approx(0.75)
