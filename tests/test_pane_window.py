import pytest
from hypothesis import given
from hypothesis import strategies as st

from helion.codec.runtime_codec import HelionRuntimeCodec
from helion.core.events import StreamEvent
from helion.factory import HelionFactory
from helion.sketches.count_min import CountMinSketch
from helion.window.pane_window import PaneWindow

PANE = 1_000
WINDOW = 3_000


def ingest(window: PaneWindow, key: str, weight: int, time: int) -> None:
    from helion.core.component import ComponentContext

    window.on_event(StreamEvent(key=key, weight=weight, event_time_millis=time), ComponentContext())


def test_closed_merge_refreshes_when_open_pane_advances_after_query():
    proto = CountMinSketch(0.05, 0.01)
    window = PaneWindow("w", proto.empty_copy(), WINDOW, PANE)
    ingest(window, "a", 1, 100)
    ingest(window, "b", 1, 1_100)
    assert window.window_total() == 2
    ingest(window, "c", 1, 2_100)
    assert window.window_total() == 3


def _retained_weight(events: list[StreamEvent], window: PaneWindow) -> int:
    if window._max_event_time == -(2**63):
        return 0
    open_start = window._pane_start(window._max_event_time)
    oldest_start = open_start - (window.max_panes() - 1) * window.pane_millis
    total = 0
    for event in events:
        if event.event_time_millis > window._max_event_time:
            continue
        start = window._pane_start(event.event_time_millis)
        if start < oldest_start:
            continue
        total += event.weight
    return total


@st.composite
def stream_events(draw):
    key = draw(st.text(min_size=1, max_size=3, alphabet="ab"))
    weight = draw(st.integers(min_value=1, max_value=3))
    time = draw(st.integers(min_value=0, max_value=20_000))
    return StreamEvent(key=key, weight=weight, event_time_millis=time)


@given(st.lists(stream_events(), min_size=1, max_size=25))
def test_queries_mid_stream_match_retained_replay(events: list[StreamEvent]) -> None:
    from helion.core.component import ComponentContext

    proto = CountMinSketch(0.05, 0.01)
    window = PaneWindow("w", proto.empty_copy(), WINDOW, PANE)
    ctx = ComponentContext()
    seen: list[StreamEvent] = []
    for event in events:
        seen.append(event)
        window.on_event(event, ctx)
        window.window_total()
        assert window.window_total() == _retained_weight(seen, window)


def test_merged_window_equals_replay_of_retained_events():
    proto = CountMinSketch(0.05, 0.01)
    window = PaneWindow("w", proto.empty_copy(), WINDOW, PANE)
    gold = proto.empty_copy()
    ingest(window, "old", 1, 100)
    ingest(window, "mid", 1, 1_100)
    ingest(window, "fresh", 1, 2_100)
    ingest(window, "fresh", 1, 3_100)
    gold.update("mid", 1)
    gold.update("fresh", 1)
    gold.update("fresh", 1)
    assert gold.total == window.window_total()
    assert gold.estimate("old") == window.estimate("old")
    assert gold.estimate("mid") == window.estimate("mid")
    assert gold.estimate("fresh") == window.estimate("fresh")
    assert window.retained_pane_count() <= window.max_panes()


def test_count_min_merge_equals_single_sketch_on_same_hashes():
    left = CountMinSketch(0.1, 0.05)
    right = left.empty_copy()
    all_sk = left.empty_copy()
    left.update("x", 3)
    right.update("y", 2)
    all_sk.update("x", 3)
    all_sk.update("y", 2)
    merged = left.empty_copy()
    merged.merge_from(left)
    merged.merge_from(right)
    assert all_sk.total == merged.total
    assert all_sk.estimate("x") == merged.estimate("x")
    assert all_sk.estimate("y") == merged.estimate("y")


def test_merge_rejects_different_hash_coefficients():
    a = CountMinSketch(0.1, 0.05)
    b = CountMinSketch(0.1, 0.05)
    a.update("x", 1)
    b.update("x", 1)
    with pytest.raises(ValueError):
        a.merge_from(b)


def test_factory_runtime_exposes_window_and_survives_codec_roundtrip():
    runtime = HelionFactory.production_with_window(0.2, 0.1, 0.4, 0.2, WINDOW, PANE)
    runtime.push(StreamEvent("hot", 1, 100))
    runtime.push(StreamEvent("hot", 1, 1_100))
    runtime.push(StreamEvent("hot", 1, 4_100))
    window = runtime.registry.get("count_min.window")
    assert isinstance(window, PaneWindow)
    assert window.window_total() == 1
    blob = HelionRuntimeCodec.encode(runtime)
    restored = HelionRuntimeCodec.decode(blob)
    restored_window = restored.registry.get("count_min.window")
    assert isinstance(restored_window, PaneWindow)
    assert window.window_total() == restored_window.window_total()
    assert window.estimate("hot") == restored_window.estimate("hot")
