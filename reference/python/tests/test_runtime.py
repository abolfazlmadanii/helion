from helion import CountMinSketch, HelionRuntime, SpaceSaving, StreamEvent
from helion.core.component import Component, ComponentContext
from helion.pipeline.hot_keys import PhiHotKeyDetector


class Probe(Component):
    def __init__(self) -> None:
        self.seen: list[object] = []

    @property
    def name(self) -> str:
        return "probe"

    def on_event(self, event: StreamEvent, context: ComponentContext) -> None:
        self.seen.append(event.key)


def test_runtime_fans_out_and_accepts_extra_component():
    probe = Probe()
    runtime = HelionRuntime(
        [
            CountMinSketch(epsilon=0.2, delta=0.1),
            SpaceSaving(capacity=3),
            PhiHotKeyDetector(phi=0.3, epsilon=0.2),
            probe,
        ]
    )
    runtime.ingest("a")
    runtime.ingest("a")
    runtime.ingest("b")
    assert probe.seen == ["a", "a", "b"]
    assert runtime.context.total_events == 3
    assert "probe" in runtime.snapshots()
    runtime.close()
