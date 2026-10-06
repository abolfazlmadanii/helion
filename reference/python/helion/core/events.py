from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Hashable, Mapping


@dataclass(frozen=True, slots=True)
class StreamEvent:
    """One observation in a turnstile stream.

    weight must be a positive integer. Fractional weights are outside
    the classical Count-Min and Space-Saving theorems implemented here.
    """

    key: Hashable
    weight: int = 1
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.weight < 1:
            raise ValueError("weight must be a positive integer")
