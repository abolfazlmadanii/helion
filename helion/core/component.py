from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from typing import Any

from helion.core.events import StreamEvent


@dataclass(slots=True)
class ComponentContext:
    total_events: int = 0
    metadata: MutableMapping[str, Any] = field(default_factory=dict)

    def note(self, name: str, value: Any) -> None:
        self.metadata[name] = value


class Component(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier used by the registry."""

    def configure(self, context: ComponentContext) -> None:
        return None

    @abstractmethod
    def on_event(self, event: StreamEvent, context: ComponentContext) -> None:
        """Process one event."""

    def snapshot(self) -> Mapping[str, Any]:
        return {"name": self.name}

    def close(self) -> None:
        return None
