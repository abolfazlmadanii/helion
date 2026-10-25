from __future__ import annotations

import math
from collections.abc import Iterable

from helion.core.component import Component
from helion.pipeline.hot_keys import PhiHotKeyDetector
from helion.pipeline.runtime import HelionRuntime
from helion.sketches.count_min import CountMinSketch
from helion.sketches.space_saving import SpaceSaving
from helion.window.pane_window import PaneWindow


class HelionFactory:
    @staticmethod
    def production(
        cms_epsilon: float,
        cms_delta: float,
        phi: float,
        ss_epsilon: float,
        extras: Iterable[Component] | None = None,
        *,
        cms_hash_seed: int | None = None,
    ) -> HelionRuntime:
        components: list[Component] = [
            CountMinSketch(cms_epsilon, cms_delta, hash_seed=cms_hash_seed),
            SpaceSaving(capacity=math.ceil(1.0 / ss_epsilon)),
            PhiHotKeyDetector(phi=phi, epsilon=ss_epsilon),
        ]
        if extras:
            components.extend(extras)
        return HelionRuntime(components)

    @staticmethod
    def production_with_window(
        cms_epsilon: float,
        cms_delta: float,
        phi: float,
        ss_epsilon: float,
        window_millis: int,
        pane_millis: int,
        extras: Iterable[Component] | None = None,
    ) -> HelionRuntime:
        all_extras: list[Component] = []
        if extras:
            all_extras.extend(extras)
        all_extras.append(
            HelionFactory.pane_count_min(cms_epsilon, cms_delta, window_millis, pane_millis)
        )
        return HelionFactory.production(cms_epsilon, cms_delta, phi, ss_epsilon, all_extras)

    @staticmethod
    def pane_count_min(
        cms_epsilon: float,
        cms_delta: float,
        window_millis: int,
        pane_millis: int,
    ) -> PaneWindow:
        proto = CountMinSketch(cms_epsilon, cms_delta, name="count_min.window.prototype")
        return PaneWindow("count_min.window", proto, window_millis, pane_millis)
