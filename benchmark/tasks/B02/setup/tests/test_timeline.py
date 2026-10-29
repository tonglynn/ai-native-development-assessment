from simkit.timeline import sample_times


def test_sample_times_count():
    assert len(sample_times(0.0, 0.5, 4)) == 4
