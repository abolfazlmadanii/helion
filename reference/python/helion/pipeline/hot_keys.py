from __future__ import annotations

import math
from collections.abc import Mapping

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

    def snapshot(self) -> Mapping[str, object]:
        return {
            "name": self.name,
            "phi": self.phi,
            "epsilon": self.epsilon,
            "capacity": self.sketch.capacity,
            "hot_key_count": len(self.hot_keys()),
            "inner": dict(self.sketch.snapshot()),
        }
