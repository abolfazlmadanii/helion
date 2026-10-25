from __future__ import annotations

import random

from helion.core.events import StreamEvent
from helion_flink.cms import cms_digest
from helion_flink.reference import reference_output
from helion_quix.config import HelionQuixConfig
from helion_quix.processor import apply_helion, replay_events


def _seeded_events(seed: int, count: int) -> list[StreamEvent]:
    rng = random.Random(seed)
    events: list[StreamEvent] = []
    for i in range(count):
        key = f"k{rng.randint(0, 11)}"
        weight = 1 + rng.randint(0, 2)
        time = 1_000 + i * 100
        events.append(StreamEvent(key=key, weight=weight, event_time_millis=time))
    return events


def _reference_bytes(events: list[StreamEvent], cfg: HelionQuixConfig) -> bytes:
    return reference_output(
        events,
        cfg.cms_epsilon,
        cfg.cms_delta,
        cfg.phi,
        cfg.ss_epsilon,
    )


def test_replay_matches_reference_on_single_partition_key() -> None:
    cfg = HelionQuixConfig()
    events = _seeded_events(11, 60)
    expected = _reference_bytes(events, cfg)

    hot_lines, runtime_blob = replay_events(events, cfg)
    keys = sorted({e.key for e in events}, key=lambda k: repr(k))
    assert runtime_blob is not None
    lines = list(hot_lines)
    lines.append("CMS:" + cms_digest(runtime_blob, keys).rstrip("\n"))
    actual = ("\n".join(lines) + "\n").encode("utf-8")
    assert actual == expected


def _bytes_state() -> object:
    store: dict[bytes, bytes] = {}

    class _BytesState:
        def get_bytes(self, key: bytes, default: bytes | None = None) -> bytes | None:
            return store.get(key, default)

        def set_bytes(self, key: bytes, value: bytes) -> None:
            store[key] = value

    return _BytesState()


def test_partition_keys_keep_isolated_state() -> None:
    cfg = HelionQuixConfig()
    state_a = _bytes_state()
    state_b = _bytes_state()
    apply_helion(
        {"key": "a", "weight": 3, "event_time_millis": 1},
        state_a,
        cfg,
    )
    apply_helion(
        {"key": "b", "weight": 1, "event_time_millis": 2},
        state_b,
        cfg,
    )
    assert state_a.get_bytes(b"helion-runtime") != state_b.get_bytes(b"helion-runtime")
