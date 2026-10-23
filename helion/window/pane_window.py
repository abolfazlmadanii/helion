from __future__ import annotations

import struct
from collections import deque
from dataclasses import dataclass
from typing import BinaryIO

from helion.codec.binary import read_string, write_string
from helion.core.component import Component, ComponentContext
from helion.core.events import StreamEvent
from helion.sketches.count_min import CountMinSketch
from helion.sketches.mergeable import MergeableSketch


@dataclass
class _Pane:
    start_millis: int
    sketch: MergeableSketch


class PaneWindow(Component):
    def __init__(
        self,
        name: str,
        prototype: MergeableSketch,
        window_millis: int,
        pane_millis: int,
    ) -> None:
        if not name:
            raise ValueError("name is required")
        if window_millis < pane_millis or window_millis % pane_millis != 0:
            raise ValueError("window_millis must be a positive multiple of pane_millis")
        self._name = name
        self._prototype = prototype
        self.window_millis = window_millis
        self.pane_millis = pane_millis
        self._max_panes = window_millis // pane_millis
        self._panes: deque[_Pane] = deque()
        self._max_event_time = -(2**63)
        self._closed_merge: MergeableSketch | None = None
        self._closed_merge_valid = False

    @property
    def name(self) -> str:
        return self._name

    def on_event(self, event: StreamEvent, context: ComponentContext) -> None:
        t = event.event_time_millis
        if t > self._max_event_time:
            self._max_event_time = t
            self._expire()
        start = self._pane_start(t)
        open_start = self._pane_start(self._max_event_time)
        oldest_start = open_start - (self._max_panes - 1) * self.pane_millis
        if start < oldest_start:
            return
        pane = self._pane_at(start)
        if pane is None:
            pane = _Pane(start, self._prototype.empty_copy())
            self._insert(pane)
        pane.sketch.update(event.key, event.weight)
        if start != open_start:
            self._closed_merge_valid = False

    def estimate(self, key: object) -> int:
        return self.merged().estimate(key)

    def window_total(self) -> int:
        return self.merged().total

    def merged(self) -> MergeableSketch:
        acc = self._prototype.empty_copy()
        if not self._closed_merge_valid:
            self._rebuild_closed_merge()
        if self._closed_merge is not None:
            acc.merge_from(self._closed_merge)
        open_pane = self._open_pane()
        if open_pane is not None:
            acc.merge_from(open_pane.sketch)
        return acc

    def retained_pane_count(self) -> int:
        return len(self._panes)

    def max_panes(self) -> int:
        return self._max_panes

    def snapshot(self) -> dict[str, object]:
        return {
            "name": self.name,
            "algorithm": "pane_window",
            "window_millis": self.window_millis,
            "pane_millis": self.pane_millis,
            "max_panes": self._max_panes,
            "retained_panes": len(self._panes),
            "window_total": 0 if not self._panes else self.window_total(),
        }

    def encode_state(self, out: BinaryIO) -> None:
        if not isinstance(self._prototype, CountMinSketch):
            raise ValueError("only Count-Min pane prototypes are supported in state codec")
        write_string(out, self._name)
        out.write(
            struct.pack(
                ">qqq",
                self.window_millis,
                self.pane_millis,
                self._max_event_time if self._max_event_time != -(2**63) else 0,
            )
        )
        self._prototype.encode_state(out)
        out.write(struct.pack(">i", len(self._panes)))
        for pane in self._panes:
            out.write(struct.pack(">q", pane.start_millis))
            if not isinstance(pane.sketch, CountMinSketch):
                raise ValueError("pane sketch must be Count-Min")
            pane.sketch.encode_state(out)

    @classmethod
    def decode_state(cls, inp: BinaryIO) -> PaneWindow:
        name = read_string(inp)
        window_millis, pane_millis, max_event_time = struct.unpack(">qqq", inp.read(24))
        prototype = CountMinSketch.decode_state(inp)
        window = cls(name, prototype, window_millis, pane_millis)
        window._max_event_time = max_event_time
        pane_count = struct.unpack(">i", inp.read(4))[0]
        for _ in range(pane_count):
            start = struct.unpack(">q", inp.read(8))[0]
            sketch = CountMinSketch.decode_state(inp)
            window._panes.append(_Pane(start, sketch))
        return window

    def _expire(self) -> None:
        if self._max_event_time == -(2**63):
            return
        oldest_start = (
            self._pane_start(self._max_event_time) - (self._max_panes - 1) * self.pane_millis
        )
        dropped = False
        while self._panes and self._panes[0].start_millis < oldest_start:
            self._panes.popleft()
            dropped = True
        if dropped:
            self._closed_merge_valid = False

    def _pane_start(self, event_time: int) -> int:
        q = event_time // self.pane_millis
        return q * self.pane_millis

    def _pane_at(self, start: int) -> _Pane | None:
        for pane in self._panes:
            if pane.start_millis == start:
                return pane
        return None

    def _open_pane(self) -> _Pane | None:
        if not self._panes or self._max_event_time == -(2**63):
            return None
        open_start = self._pane_start(self._max_event_time)
        last = self._panes[-1]
        return last if last.start_millis == open_start else None

    def _insert(self, pane: _Pane) -> None:
        if not self._panes or pane.start_millis >= self._panes[-1].start_millis:
            self._panes.append(pane)
            return
        rest: deque[_Pane] = deque()
        while self._panes and self._panes[-1].start_millis > pane.start_millis:
            rest.appendleft(self._panes.pop())
        self._panes.append(pane)
        self._panes.extend(rest)
        self._closed_merge_valid = False

    def _rebuild_closed_merge(self) -> None:
        acc = self._prototype.empty_copy()
        open_start = (
            self._pane_start(self._max_event_time)
            if self._max_event_time != -(2**63)
            else -(2**63)
        )
        for pane in self._panes:
            if pane.start_millis != open_start:
                acc.merge_from(pane.sketch)
        self._closed_merge = acc
        self._closed_merge_valid = True
