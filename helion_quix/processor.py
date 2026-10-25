from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quixstreams.state.base.state import State

from helion.codec.runtime_codec import HelionRuntimeCodec
from helion.core.events import StreamEvent
from helion.factory import HelionFactory
from helion.pipeline.hot_keys import PhiHotKeyDetector
from helion_quix.config import RUNTIME_STATE_KEY, HelionQuixConfig


def event_from_message(value: Mapping[str, Any]) -> StreamEvent:
    return StreamEvent(
        key=value["key"],
        weight=int(value["weight"]),
        event_time_millis=int(value["event_time_millis"]),
    )


def apply_helion(value: dict[str, Any], state: State, cfg: HelionQuixConfig) -> dict[str, Any]:
    """
    Stateful step used by the Quix Streams dataframe.

    Kafka message keys isolate state; each key keeps a HelionRuntimeCodec blob.
    """
    event = event_from_message(value)
    blob = state.get_bytes(RUNTIME_STATE_KEY)
    runtime = (
        HelionRuntimeCodec.decode(blob)
        if blob
        else HelionFactory.production(
            cfg.cms_epsilon,
            cfg.cms_delta,
            cfg.phi,
            cfg.ss_epsilon,
            cms_hash_seed=cfg.cms_hash_seed,
        )
    )
    runtime.push(event)
    state.set_bytes(RUNTIME_STATE_KEY, HelionRuntimeCodec.encode(runtime))

    hot_lines: list[str] = []
    detector = runtime.registry.get("phi_hot_keys")
    if isinstance(detector, PhiHotKeyDetector):
        for row in detector.hot_keys():
            hot_lines.append(
                f"{row.key},{row.estimate},{row.error},{row.total_events},{cfg.phi}"
            )

    return {
        "key": event.key,
        "weight": event.weight,
        "event_time_millis": event.event_time_millis,
        "hot_keys": hot_lines,
    }


def replay_events(
    events: list[StreamEvent],
    cfg: HelionQuixConfig | None = None,
) -> tuple[list[str], bytes | None]:
    """Drive :func:`apply_helion` in-process (no broker) for deterministic tests."""
    cfg = cfg or HelionQuixConfig()
    store: dict[bytes, bytes] = {}
    hot_lines: list[str] = []

    class _BytesState:
        def get_bytes(self, key: bytes, default: bytes | None = None) -> bytes | None:
            return store.get(key, default)

        def set_bytes(self, key: bytes, value: bytes) -> None:
            store[key] = value

    state = _BytesState()
    for event in events:
        payload = {
            "key": event.key,
            "weight": event.weight,
            "event_time_millis": event.event_time_millis,
        }
        result = apply_helion(payload, state, cfg)
        hot_lines.extend(result["hot_keys"])

    return hot_lines, store.get(RUNTIME_STATE_KEY)
