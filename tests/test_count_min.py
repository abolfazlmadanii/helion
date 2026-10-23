import math
from collections import Counter

from hypothesis import given
from hypothesis import strategies as st

from helion.sketches.count_min import CountMinSketch


def test_never_underestimates():
    sketch = CountMinSketch(epsilon=0.05, delta=0.01)
    stream = ["a"] * 40 + ["b"] * 15 + ["c"] * 7 + ["d"] * 3
    for key in stream:
        sketch.update(key)
    truth = Counter(stream)
    for key, freq in truth.items():
        assert sketch.estimate(key) >= freq


@given(st.lists(st.text(min_size=1, max_size=8), min_size=1, max_size=200))
def test_never_underestimates_hypothesis(keys):
    sketch = CountMinSketch(epsilon=0.05, delta=0.01)
    truth: Counter[str] = Counter()
    for key in keys:
        sketch.update(key)
        truth[key] += 1
    for key, freq in truth.items():
        assert sketch.estimate(key) >= freq


def test_width_depth_match_theorem():
    eps, delta = 0.01, 1e-4
    sketch = CountMinSketch(epsilon=eps, delta=delta)
    assert sketch.width == math.ceil(math.e / eps)
    assert sketch.depth == math.ceil(math.log(1.0 / delta))
