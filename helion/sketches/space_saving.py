from __future__ import annotations

import struct
from collections.abc import Hashable, Iterator, Mapping
from dataclasses import dataclass
from typing import BinaryIO

from helion.codec.binary import read_string, write_string
from helion.core.component import Component, ComponentContext
from helion.core.events import StreamEvent


@dataclass(slots=True)
class _Bucket:
    count: int
    keys: dict[Hashable, _Entry]
    lesser: _Bucket | None = None
    greater: _Bucket | None = None


@dataclass(slots=True)
class _Entry:
    key: Hashable
    error: int
    bucket: _Bucket


@dataclass(frozen=True, slots=True)
class SpaceSavingEstimate:
    key: Hashable
    estimate: int
    error: int
    monitored: bool
    total_events: int
    capacity: int

    @property
    def lower_bound(self) -> int:
        """f(x) ≥ estimate − error ≥ estimate − N/m for monitored keys."""
        if not self.monitored:
            return 0
        return max(0, self.estimate - self.error)

    @property
    def upper_bound(self) -> int:
        """Monitored: hat. Unmonitored: f(x) ≤ min_count ≤ N/m."""
        return self.estimate


class SpaceSaving(Component):
    """Space-Saving (Metwally, Agrawal, Abbadi, 2005) via Stream-Summary.

    Parameters
    ----------
    capacity :
        Number of monitored counters m ≥ 1. The additive error is N/m.
    name :
        Registry identifier.

    Deterministic guarantees (all hold for every stream, no probability)
    -------------------------------------------------------------------
    1. Sum of the m counters equals N, the total weight.
    2. The minimum counter is at most N/m.
    3. For every monitored key x:  f(x) ≤ f̂(x) ≤ f(x) + N/m.
    4. Every key with f(x) > N/m is monitored (no false negatives above N/m).
    """

    def __init__(self, capacity: int, *, name: str = "space_saving") -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._name = name
        self.capacity = int(capacity)
        self.total = 0
        self._items: dict[Hashable, _Entry] = {}
        self._min_bucket: _Bucket | None = None

    @property
    def name(self) -> str:
        return self._name

    def update(self, key: Hashable, weight: int = 1) -> None:
        if weight < 1:
            raise ValueError("weight must be a positive integer")
        remaining = weight
        while remaining:
            self._update_one(key)
            remaining -= 1

    def _update_one(self, key: Hashable) -> None:
        self.total += 1
        if key in self._items:
            self._increment(self._items[key])
            return
        if len(self._items) < self.capacity:
            self._insert_new(key, count=1, error=0)
            return
        victim = self._evict_min()
        inherited = victim.bucket.count
        self._detach(victim)
        del self._items[victim.key]
        if not victim.bucket.keys:
            self._unlink_bucket(victim.bucket)
        self._insert_new(key, count=inherited + 1, error=inherited)

    def estimate(self, key: Hashable) -> int:
        entry = self._items.get(key)
        if entry is not None:
            return entry.bucket.count
        return self.min_count

    def query(self, key: Hashable) -> SpaceSavingEstimate:
        entry = self._items.get(key)
        if entry is None:
            cap = self.min_count
            return SpaceSavingEstimate(
                key=key,
                estimate=cap,
                error=cap,
                monitored=False,
                total_events=self.total,
                capacity=self.capacity,
            )
        return SpaceSavingEstimate(
            key=key,
            estimate=entry.bucket.count,
            error=entry.error,
            monitored=True,
            total_events=self.total,
            capacity=self.capacity,
        )

    def is_monitored(self, key: Hashable) -> bool:
        return key in self._items

    def monitored(self) -> list[SpaceSavingEstimate]:
        out = [self.query(key) for key in self._items]
        out.sort(key=lambda row: (-row.estimate, repr(row.key)))
        return out

    def heavy_hitters(self, phi: float) -> list[SpaceSavingEstimate]:
        """Keys whose estimate exceeds φ N.

        If m ≥ 1/ε and ε < φ, every true hot key with f(x) > φ N is
        present. Extra keys near the threshold may appear (false positives).
        """
        if not 0 < phi < 1:
            raise ValueError("phi must lie in (0, 1)")
        threshold = phi * self.total
        return [row for row in self.monitored() if row.estimate > threshold]

    @property
    def min_count(self) -> int:
        if self._min_bucket is None:
            return 0
        return self._min_bucket.count

    def counter_sum(self) -> int:
        return sum(entry.bucket.count for entry in self._items.values())

    def on_event(self, event: StreamEvent, context: ComponentContext) -> None:
        self.update(event.key, event.weight)

    def encode_state(self, out: BinaryIO) -> None:
        write_string(out, self._name)
        out.write(struct.pack(">iqi", self.capacity, self.total, len(self._items)))
        for entry in self._items.values():
            write_string(out, str(entry.key))
            out.write(struct.pack(">qq", entry.bucket.count, entry.error))

    @classmethod
    def decode_state(cls, inp: BinaryIO) -> SpaceSaving:
        name = read_string(inp)
        capacity, total, entry_count = struct.unpack(">iqi", inp.read(16))
        sketch = cls(capacity=capacity, name=name)
        sketch.total = total
        for _ in range(entry_count):
            key = read_string(inp)
            count, error = struct.unpack(">qq", inp.read(16))
            sketch._insert_new(key, int(count), int(error))
        return sketch

    def snapshot(self) -> Mapping[str, object]:
        return {
            "name": self.name,
            "algorithm": "space_saving",
            "capacity": self.capacity,
            "monitored": len(self._items),
            "total": self.total,
            "min_count": self.min_count,
            "counter_sum": self.counter_sum(),
            "additive_error_bound": (self.total / self.capacity) if self.capacity else 0,
            "guarantee": "f <= hat <= f + N/m for monitored keys; f > N/m => monitored",
        }

    def __iter__(self) -> Iterator[SpaceSavingEstimate]:
        return iter(self.monitored())

    def _insert_new(self, key: Hashable, count: int, error: int) -> None:
        bucket = self._bucket_with_count(count, after=self._min_bucket)
        entry = _Entry(key=key, error=error, bucket=bucket)
        bucket.keys[key] = entry
        self._items[key] = entry

    def _increment(self, entry: _Entry) -> None:
        old = entry.bucket
        new_count = old.count + 1
        nxt = old.greater
        del old.keys[entry.key]
        if nxt is not None and nxt.count == new_count:
            target = nxt
        else:
            target = _Bucket(count=new_count, keys={})
            self._link_after(old, target)
        entry.bucket = target
        target.keys[entry.key] = entry
        if not old.keys:
            self._unlink_bucket(old)

    def _evict_min(self) -> _Entry:
        bucket = self._min_bucket
        if bucket is None or not bucket.keys:
            raise RuntimeError("Space-Saving invariant broken: empty structure")
        key = next(iter(bucket.keys))
        return bucket.keys[key]

    def _detach(self, entry: _Entry) -> None:
        del entry.bucket.keys[entry.key]

    def _bucket_with_count(self, count: int, after: _Bucket | None) -> _Bucket:
        if self._min_bucket is None:
            bucket = _Bucket(count=count, keys={})
            self._min_bucket = bucket
            return bucket
        node = self._min_bucket
        prev: _Bucket | None = None
        while node is not None and node.count < count:
            prev = node
            node = node.greater
        if node is not None and node.count == count:
            return node
        bucket = _Bucket(count=count, keys={})
        if prev is None:
            bucket.greater = self._min_bucket
            self._min_bucket.lesser = bucket
            self._min_bucket = bucket
        else:
            self._link_after(prev, bucket)
        _ = after
        return bucket

    def _link_after(self, left: _Bucket, new: _Bucket) -> None:
        right = left.greater
        left.greater = new
        new.lesser = left
        new.greater = right
        if right is not None:
            right.lesser = new

    def _unlink_bucket(self, bucket: _Bucket) -> None:
        left, right = bucket.lesser, bucket.greater
        if left is not None:
            left.greater = right
        else:
            self._min_bucket = right
        if right is not None:
            right.lesser = left
        bucket.lesser = None
        bucket.greater = None
