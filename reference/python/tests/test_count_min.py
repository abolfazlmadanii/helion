from collections import Counter

from helion.sketches.count_min import CountMinSketch


def test_never_underestimates():
    sketch = CountMinSketch(epsilon=0.05, delta=0.01)
    stream = ["a"] * 40 + ["b"] * 15 + ["c"] * 7 + ["d"] * 3
    for key in stream:
        sketch.update(key)
    truth = Counter(stream)
    for key, freq in truth.items():
        assert sketch.estimate(key) >= freq


def test_width_depth_match_theorem():
    import math

    eps, delta = 0.01, 1e-4
    sketch = CountMinSketch(epsilon=eps, delta=delta)
    assert sketch.width == math.ceil(math.e / eps)
    assert sketch.depth == math.ceil(math.log(1.0 / delta))


def test_snapshot_contract():
    sketch = CountMinSketch(epsilon=0.1, delta=0.2)
    sketch.update("x", 5)
    snap = sketch.snapshot()
    assert snap["algorithm"] == "count_min"
    assert snap["total"] == 5
    assert snap["width"] == sketch.width
