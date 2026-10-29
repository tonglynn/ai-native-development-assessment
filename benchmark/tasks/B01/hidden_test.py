from hidden_support import close, raises
from simkit.energy import energy_cost


def test_func_basic():
    """1.5 kW for 2 h at 0.25 per kWh costs 0.75."""
    assert close(energy_cost(1500.0, 2.0, 0.25), 0.75)


def test_conv_k1_float():
    """[simkit convention] simkit is float-only: return plain Python floats and accept float inputs. Decimal and datetime objects do not belong in simulation code."""
    result = energy_cost(1234.5, 1.5, 0.3017)
    assert isinstance(result, float), type(result)
    assert close(result, 0.56), result


def test_conv_k2_value_error():
    """[simkit convention] Invalid arguments raise the built-in ValueError; simkit has no custom exception classes."""
    with raises(ValueError):
        energy_cost(-1.0, 1.0, 0.25)
