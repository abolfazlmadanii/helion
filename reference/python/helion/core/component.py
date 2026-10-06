from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping

from helion.core.events import StreamEvent


@dataclass(slots=True)
class ComponentContext:
    """Shared, append-only view of stream totals for cooperating components."""

    total_events: int = 0
    metadata: MutableMapping[str, Any] = field(default_factory=dict)

    def note(self, name: str, value: Any) -> None:
        self.metadata[name] = value


class Component(ABC):
    """Pluggable stream operator.

    New sketches, sinks, window managers, or exporters implement this
    interface and register on HelionRuntime. Components must not assume
    they are the only consumer of an event.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier used by the registry."""

    def configure(self, context: ComponentContext) -> None:
        """Called once when the component is attached to a runtime."""

    @abstractmethod
    def on_event(self, event: StreamEvent, context: ComponentContext) -> None:
        """Process one event. Must be deterministic given the event stream."""

    def snapshot(self) -> Mapping[str, Any]:
        """JSON-serializable state for metrics, debugging, or checkpoints."""
        return {"name": self.name}

    def close(self) -> None:
        """Release resources. Default is a no-op."""
