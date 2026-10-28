from __future__ import annotations

from collections.abc import Hashable, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class StreamEvent:
    """One observation in a cash-register (insert-only) stream."""

    key: Hashable
    weight: int = 1
    event_time_millis: int = 0
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.weight < 1:
            raise ValueError("weight must be a positive integer")

    @staticmethod
    def parse_line_required(line: str) -> StreamEvent:
        if not line or not line.strip():
            raise ValueError("event line is empty")
        parts = line.strip().split(",", 2)
        if len(parts) < 3 or not parts[2].strip():
            raise ValueError("event time is required in CSV: key,weight,eventTimeMillis")
        key = parts[0].strip()
        weight = int(parts[1].strip()) if parts[1].strip() else 1
        event_time = int(parts[2].strip())
        return StreamEvent(key=key, weight=weight, event_time_millis=event_time)

    @staticmethod
    def parse_line(line: str, fallback_event_time_millis: int) -> StreamEvent:
        if not line or not line.strip():
            raise ValueError("event line is empty")
        parts = line.strip().split(",", 2)
        key = parts[0].strip()
        if len(parts) == 1 or not parts[1].strip():
            return StreamEvent(key=key, weight=1, event_time_millis=fallback_event_time_millis)
        weight = int(parts[1].strip())
        time = fallback_event_time_millis
        if len(parts) == 3 and parts[2].strip():
            time = int(parts[2].strip())
        return StreamEvent(key=key, weight=weight, event_time_millis=time)
