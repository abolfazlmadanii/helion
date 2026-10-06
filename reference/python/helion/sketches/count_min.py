from __future__ import annotations

import math
from array import array
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Hashable, Sequence

from helion.core.component import Component, ComponentContext
from helion.core.events import StreamEvent
from helion.core.hashing import carter_wegman, draw_cw_pair, key_to_uint


@dataclass(frozen=True, slots=True)
class CountMinEstimate:
    key: Hashable
    estimate: int
    true_lower_bound: int
    additive_slack: float
    failure_probability: float
    total_events: int


class CountMinSketch(Component):
    """Count-Min Sketch of Cormode and Muthukrishnan (2005).

    Parameters
    ----------
    epsilon :
        Additive slack ε > 0. Width is w = ceil(e / ε).
    delta :
        Failure probability δ ∈ (0, 1). Depth is d = ceil(ln(1/δ)).
    name :
        Registry identifier so multiple CMS instances can coexist.

    Theorem (one-sided concentration)
    ---------------------------------
    Let N = sum of weights observed. For every key x,

        f(x)  ≤  f̂(x)  ≤  f(x) + ε N

    holds with probability at least 1 − δ over the hash draws. The left
    inequality is deterministic: every update of x increments every
    hashed cell, so no estimate can fall below the true frequency.
    """

    def __init__(
        self,
        epsilon: float = 0.001,
        delta: float = 1e-4,
        *,
        name: str = "count_min",
    ) -> None:
        if epsilon <= 0:
            raise ValueError("epsilon must be positive")
        if not 0 < delta < 1:
            raise ValueError("delta must lie in (0, 1)")
        self._name = name
        self.epsilon = float(epsilon)
        self.delta = float(delta)
        self.width = math.ceil(math.e / self.epsilon)
        self.depth = math.ceil(math.log(1.0 / self.delta))
        self._coeffs: list[tuple[int, int]] = [draw_cw_pair() for _ in range(self.depth)]
        self._table: list[array] = [
            array("Q", [0] * self.width) for _ in range(self.depth)
        ]
        self.total = 0

    @property
    def name(self) -> str:
        return self._name

    def _columns(self, key: Hashable) -> list[int]:
        x = key_to_uint(key)
        return [carter_wegman(x, a, b, self.width) for a, b in self._coeffs]

    def update(self, key: Hashable, weight: int = 1) -> None:
        if weight < 1:
            raise ValueError("weight must be a positive integer")
        cols = self._columns(key)
        for row, col in enumerate(cols):
            self._table[row][col] += weight
        self.total += weight

    def estimate(self, key: Hashable) -> int:
        cols = self._columns(key)
        return min(self._table[row][col] for row, col in enumerate(cols))

    def query(self, key: Hashable) -> CountMinEstimate:
        hat = self.estimate(key)
        return CountMinEstimate(
            key=key,
            estimate=hat,
            true_lower_bound=0,
            additive_slack=self.epsilon * self.total,
            failure_probability=self.delta,
            total_events=self.total,
        )

    def on_event(self, event: StreamEvent, context: ComponentContext) -> None:
        self.update(event.key, event.weight)

    def snapshot(self) -> Mapping[str, object]:
        return {
            "name": self.name,
            "algorithm": "count_min",
            "epsilon": self.epsilon,
            "delta": self.delta,
            "width": self.width,
            "depth": self.depth,
            "total": self.total,
            "cells": self.depth * self.width,
            "guarantee": "P(f <= hat <= f + eps*N) >= 1-delta",
        }

    def row_view(self, row: int) -> Sequence[int]:
        return tuple(self._table[row])
