from voxrubric.arena import _bootstrap_mean_ci


def test_bootstrap_mean_ci_is_reproducible():
    values = [0.2, 0.4, 0.8, 1.0]
    first = _bootstrap_mean_ci(values)
    second = _bootstrap_mean_ci(values)

    assert first == second
    low, high = first
    assert low is not None
    assert high is not None
    assert low <= sum(values) / len(values) <= high


def test_bootstrap_mean_ci_requires_repeated_runs():
    assert _bootstrap_mean_ci([0.7]) == (None, None)


def test_bootstrap_mean_ci_collapses_for_constant_metric():
    low, high = _bootstrap_mean_ci([0.5, 0.5, 0.5, 0.5])
    assert low == 0.5
    assert high == 0.5
