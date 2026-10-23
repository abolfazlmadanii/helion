from collections import Counter

from helion import CountMinSketch, HelionRuntime, SpaceSaving, StreamEvent
from helion.core.component import Component, ComponentContext
from helion.pipeline.hot_keys import PhiHotKeyDetector


class CountingComponent(Component):
    def __init__(self) -> None:
        self.count = 0

    @property
    def name(self) -> str:
        return "probe"

    def on_event(self, event: StreamEvent, context: ComponentContext) -> None:
        self.count += 1


def test_parse_line_accepts_weight_and_event_time():
    event = StreamEvent.parse_line("k,3,42", 0)
    assert event.key == "k"
    assert event.weight == 3
    assert event.event_time_millis == 42


def test_space_saving_sum_equals_n_and_heavy_keys_stay():
    ss = SpaceSaving(capacity=3)
    stream = ["hot"] * 20 + ["a", "a", "b", "b", "c", "c", "d", "d"]
    truth: Counter[str] = Counter()
    for key in stream:
        ss.update(key)
        truth[key] += 1
    assert ss.counter_sum() == len(stream)
    assert ss.total == len(stream)
    assert ss.min_count <= ss.total / ss.capacity
    bound = ss.total / ss.capacity
    for key, freq in truth.items():
        if freq > bound:
            assert ss.is_monitored(key)
    for row in ss.monitored():
        f = truth[row.key]
        assert f <= row.estimate
        assert row.estimate <= f + bound + 1e-9


def test_runtime_accepts_extra_component():
    probe = CountingComponent()
    runtime = HelionRuntime(
        [
            CountMinSketch(0.2, 0.1),
            SpaceSaving(3),
            PhiHotKeyDetector(phi=0.3, epsilon=0.2),
            probe,
        ]
    )
    runtime.push(StreamEvent("a"))
    runtime.push(StreamEvent("a"))
    runtime.push(StreamEvent("b"))
    assert probe.count == 3
    assert runtime.total_weight == 3
    assert "probe" in runtime.snapshots()
