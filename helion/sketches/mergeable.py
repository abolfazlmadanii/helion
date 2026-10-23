from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MergeableSketch(Protocol):
    def empty_copy(self) -> MergeableSketch:
        ...

    def update(self, key: object, weight: int = 1) -> None:
        ...

    def merge_from(self, other: MergeableSketch) -> None:
        ...

    def estimate(self, key: object) -> int:
        ...

    @property
    def total(self) -> int:
        ...
