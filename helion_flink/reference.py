from __future__ import annotations

from helion.codec.runtime_codec import HelionRuntimeCodec
from helion.core.events import StreamEvent
from helion.factory import HelionFactory
from helion.pipeline.hot_keys import PhiHotKeyDetector
from helion_flink.cms import cms_digest
from helion_flink.config import CMS_HASH_SEED


def reference_output(
    events: list[StreamEvent],
    cms_epsilon: float,
    cms_delta: float,
    phi: float,
    ss_epsilon: float,
) -> bytes:
    runtime = HelionFactory.production(
        cms_epsilon, cms_delta, phi, ss_epsilon, cms_hash_seed=CMS_HASH_SEED
    )
    lines: list[str] = []
    keys_seen: set[object] = set()
    for event in events:
        keys_seen.add(event.key)
        runtime.push(event)
        detector = runtime.registry.get("phi_hot_keys")
        if isinstance(detector, PhiHotKeyDetector):
            for row in detector.hot_keys():
                lines.append(
                    f"{row.key},{row.estimate},{row.error},{row.total_events},{phi}"
                )
    cms_blob = HelionRuntimeCodec.encode(runtime)
    lines.append("CMS:" + cms_digest(cms_blob, list(keys_seen)).rstrip("\n"))
    return ("\n".join(lines) + "\n").encode("utf-8")
