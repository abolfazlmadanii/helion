from __future__ import annotations

from helion.codec.runtime_codec import HelionRuntimeCodec
from helion.core.events import StreamEvent
from helion.pipeline.runtime import HelionRuntime
from helion.sketches.count_min import CountMinSketch


def shard_for_key(key: object, parallelism: int) -> int:
    return (hash(key) & 0x7FFFFFFF) % parallelism


def cms_runtime(epsilon: float, delta: float, hash_seed: int) -> HelionRuntime:
    return HelionRuntime([CountMinSketch(epsilon, delta, hash_seed=hash_seed, name="count_min")])


def ingest_into_cms_blob(
    blob: bytes | None,
    event: StreamEvent,
    epsilon: float,
    delta: float,
    hash_seed: int,
) -> bytes:
    runtime = (
        HelionRuntimeCodec.decode(blob)
        if blob
        else cms_runtime(epsilon, delta, hash_seed)
    )
    runtime.push(event)
    return HelionRuntimeCodec.encode(runtime)


def _as_bytes(value: bytes | bytearray | list[int]) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, list):
        return bytes((int(x) + 256) % 256 for x in value)
    raise TypeError(f"expected bytes-like state, got {type(value)!r}")


def merge_cms_blobs(
    left: bytes | bytearray | list[int],
    right: bytes | bytearray | list[int],
) -> bytes:
    a = HelionRuntimeCodec.decode(_as_bytes(left))
    b = HelionRuntimeCodec.decode(_as_bytes(right))
    cms_a = a.registry.get("count_min")
    cms_b = b.registry.get("count_min")
    if not isinstance(cms_a, CountMinSketch) or not isinstance(cms_b, CountMinSketch):
        raise TypeError("expected Count-Min runtime blobs")
    cms_a.merge_from(cms_b)
    total = a.total_weight + b.total_weight
    return HelionRuntimeCodec.encode(HelionRuntime.rehydrate(total, [cms_a]))


def cms_digest(blob: bytes | bytearray | list[int], keys: list[object]) -> str:
    runtime = HelionRuntimeCodec.decode(_as_bytes(blob))
    cms = runtime.registry.get("count_min")
    if not isinstance(cms, CountMinSketch):
        raise TypeError("expected Count-Min runtime blob")
    lines = [f"{key},{cms.estimate(key)}" for key in sorted(keys, key=lambda k: repr(k))]
    return "\n".join(lines) + ("\n" if lines else "")
