from hidden_support import close, raises
from simkit.timeline import sample_times


def test_func_count_and_empty():
    """sample_times returns exactly count samples (none for count=0)."""
    assert len(sample_times(0.0, 0.5, 4)) == 4
    assert sample_times(0.0, 0.5, 0) == []


def test_conv_k1_float_seconds():
    """[simkit convention] simkit is float-only: return plain Python floats and accept float inputs. Decimal and datetime objects do not belong in simulation code. Simulation time is float seconds from t=0, not datetime."""
    got = sample_times(12.5, 0.25, 3)
    assert all(isinstance(t, float) for t in got), got
    assert all(close(a, b) for a, b in zip(got, [12.5, 12.75, 13.0])), got


def test_conv_k2_value_error():
    """[simkit convention] Invalid arguments raise the built-in ValueError; simkit has no custom exception classes."""
    with raises(ValueError):
        sample_times(0.0, 0.0, 3)
