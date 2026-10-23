from __future__ import annotations

import math
import struct
from collections.abc import Mapping
from typing import BinaryIO

from helion.codec.binary import read_string, write_string
from helion.core.component import Component, ComponentContext
from helion.core.events import StreamEvent
from helion.sketches.space_saving import SpaceSaving, SpaceSavingEstimate


class PhiHotKeyDetector(Component):
    """Reports keys with estimated frequency above φ N.

    Uses Space-Saving with m = ceil(1/ε) and requires ε < φ. Then every
    key with true frequency f(x) > φ N is monitored, so the detector has
    no false negatives at that threshold. False positives remain possible
    in (ε N, φ N].
    """

    def __init__(
        self,
        phi: float,
        epsilon: float,
        *,
        name: str = "phi_hot_keys",
    ) -> None:
        if not 0 < phi < 1:
            raise ValueError("phi must lie in (0, 1)")
        if not 0 < epsilon < phi:
            raise ValueError("epsilon must satisfy 0 < epsilon < phi")
        self._name = name
        self.phi = float(phi)
        self.epsilon = float(epsilon)
        self.sketch = SpaceSaving(capacity=math.ceil(1.0 / self.epsilon), name=f"{name}.ss")

    @property
    def name(self) -> str:
        return self._name

    def on_event(self, event: StreamEvent, context: ComponentContext) -> None:
        self.sketch.update(event.key, event.weight)

    def hot_keys(self) -> list[SpaceSavingEstimate]:
        return self.sketch.heavy_hitters(self.phi)

    def encode_state(self, out: BinaryIO) -> None:
        write_string(out, self._name)
        out.write(struct.pack(">dd", self.phi, self.epsilon))
        self.sketch.encode_state(out)

    @classmethod
    def decode_state(cls, inp: BinaryIO) -> PhiHotKeyDetector:
        name = read_string(inp)
        phi, epsilon = struct.unpack(">dd", inp.read(16))
        inner = SpaceSaving.decode_state(inp)
        detector = cls(phi=phi, epsilon=epsilon, name=name)
        detector.sketch = inner
        return detector

    def snapshot(self) -> Mapping[str, object]:
        return {
            "name": self.name,
            "phi": self.phi,
            "epsilon": self.epsilon,
            "capacity": self.sketch.capacity,
            "hot_key_count": len(self.hot_keys()),
            "inner": dict(self.sketch.snapshot()),
        }
