import pytest

from helion.codec.binary import CodecError
from helion.codec.runtime_codec import HelionRuntimeCodec
from helion.core.events import StreamEvent
from helion.factory import HelionFactory
from helion.sketches.count_min import CountMinSketch


def test_round_trip_production_runtime():
    runtime = HelionFactory.production_with_window(0.2, 0.1, 0.4, 0.2, 3_000, 1_000)
    runtime.push(StreamEvent("hot", 1, 100))
    runtime.push(StreamEvent("hot", 1, 1_100))
    blob = HelionRuntimeCodec.encode(runtime)
    restored = HelionRuntimeCodec.decode(blob)
    assert restored.total_weight == runtime.total_weight
    cms = restored.registry.get("count_min")
    assert isinstance(cms, CountMinSketch)
    assert cms.estimate("hot") == 2


def test_rejects_unknown_version():
    runtime = HelionFactory.production(0.2, 0.1, 0.4, 0.2)
    blob = bytearray(HelionRuntimeCodec.encode(runtime))
    blob[7] = 99
    with pytest.raises(CodecError):
        HelionRuntimeCodec.decode(bytes(blob))
