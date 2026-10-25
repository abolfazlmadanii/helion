from __future__ import annotations

import math
import random
import struct
from array import array
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, BinaryIO

if TYPE_CHECKING:
    from helion.sketches.mergeable import MergeableSketch

from helion.codec.binary import (
    read_long_array,
    read_long_matrix,
    read_string,
    write_long_array,
    write_long_matrix,
    write_string,
)
from helion.core.component import Component, ComponentContext
from helion.core.events import StreamEvent
from helion.core.hashing import carter_wegman, draw_cw_pair, draw_cw_pair_from_rng, key_to_uint


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
        hash_seed: int | None = None,
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
        if hash_seed is None:
            self._coeffs = [draw_cw_pair() for _ in range(self.depth)]
        else:
            rng = random.Random(hash_seed)
            self._coeffs = [draw_cw_pair_from_rng(rng) for _ in range(self.depth)]
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

    def empty_copy(self) -> CountMinSketch:
        return CountMinSketch._from_coeffs(
            self._name,
            self.epsilon,
            self.delta,
            self.width,
            self.depth,
            list(self._coeffs),
        )

    def merge_from(self, other: MergeableSketch) -> None:
        if not isinstance(other, CountMinSketch):
            raise ValueError("Count-Min can only merge another Count-Min")
        if (
            self.width != other.width
            or self.depth != other.depth
            or self.epsilon != other.epsilon
            or self.delta != other.delta
        ):
            raise ValueError("Count-Min dimensions must match")
        if self._coeffs != other._coeffs:
            raise ValueError("Count-Min hash coefficients must match")
        for row in range(self.depth):
            for col in range(self.width):
                self._table[row][col] += other._table[row][col]
        self.total += other.total

    @classmethod
    def _from_coeffs(
        cls,
        name: str,
        epsilon: float,
        delta: float,
        width: int,
        depth: int,
        coeffs: list[tuple[int, int]],
    ) -> CountMinSketch:
        sketch = cls.__new__(cls)
        sketch._name = name
        sketch.epsilon = epsilon
        sketch.delta = delta
        sketch.width = width
        sketch.depth = depth
        sketch._coeffs = list(coeffs)
        sketch._table = [array("Q", [0] * width) for _ in range(depth)]
        sketch.total = 0
        return sketch

    def encode_state(self, out: BinaryIO) -> None:
        write_string(out, self._name)
        out.write(struct.pack(">ddii", self.epsilon, self.delta, self.width, self.depth))
        write_long_array(out, [a for a, _ in self._coeffs])
        write_long_array(out, [b for _, b in self._coeffs])
        write_long_matrix(out, self._table)
        out.write(struct.pack(">q", self.total))

    @classmethod
    def decode_state(cls, inp: BinaryIO) -> CountMinSketch:
        name = read_string(inp)
        epsilon, delta, width, depth = struct.unpack(">ddii", inp.read(24))
        a_vals = read_long_array(inp)
        b_vals = read_long_array(inp)
        table_vals = read_long_matrix(inp)
        total = struct.unpack(">q", inp.read(8))[0]
        coeffs = list(zip(a_vals, b_vals, strict=True))
        sketch = cls._from_coeffs(name, epsilon, delta, width, depth, coeffs)
        for row in range(depth):
            for col in range(width):
                sketch._table[row][col] = table_vals[row][col]
        sketch.total = total
        return sketch
