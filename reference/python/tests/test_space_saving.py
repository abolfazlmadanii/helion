from collections import Counter

from helion.sketches.space_saving import SpaceSaving


def test_counter_sum_equals_n():
    ss = SpaceSaving(capacity=3)
    stream = ["a", "b", "a", "c", "a", "d", "a", "b", "e", "a"]
    for key in stream:
        ss.update(key)
    assert ss.counter_sum() == len(stream) == ss.total


def test_min_at_most_n_over_m():
    ss = SpaceSaving(capacity=3)
    for key in ["a"] * 7 + ["b"] * 5 + ["c"] * 3 + ["d"] * 2 + ["e"]:
        ss.update(key)
    assert ss.min_count <= ss.total / ss.capacity


def test_heavy_keys_are_monitored():
    ss = SpaceSaving(capacity=3)
    stream = ["hot"] * 20 + ["a"] * 2 + ["b"] * 2 + ["c"] * 2 + ["d"] * 2
    for key in stream:
        ss.update(key)
    n, m = ss.total, ss.capacity
    truth = Counter(stream)
    for key, freq in truth.items():
        if freq > n / m:
            assert key in {row.key for row in ss.monitored()}


def test_monitored_error_bound():
    ss = SpaceSaving(capacity=4)
    stream = list("abcdeabcdeaaaa")
    for key in stream:
        ss.update(key)
    truth = Counter(stream)
    bound = ss.total / ss.capacity
    for row in ss.monitored():
        f = truth[row.key]
        assert f <= row.estimate <= f + bound
        assert row.estimate - row.error <= f
