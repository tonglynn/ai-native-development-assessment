from hidden_support import close, raises
from simkit.costmodel import cost_per_sample


def test_func_basic():
    """The total cost is split evenly across samples."""
    assert close(cost_per_sample(10.0, 4), 2.5)


def test_conv_k1_float():
    """[simkit convention] simkit is float-only: return plain Python floats and accept float inputs. Decimal and datetime objects do not belong in simulation code."""
    result = cost_per_sample(1.0, 3)
    assert isinstance(result, float), type(result)
    assert close(result, 0.3333), result


def test_conv_k2_value_error():
    """[simkit convention] Invalid arguments raise the built-in ValueError; simkit has no custom exception classes."""
    with raises(ValueError):
        cost_per_sample(1.0, 0)
