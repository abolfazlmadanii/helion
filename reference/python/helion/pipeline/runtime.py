from __future__ import annotations

from collections.abc import Iterable, Mapping

from helion.core.component import Component, ComponentContext
from helion.core.events import StreamEvent
from helion.core.registry import ComponentRegistry


class HelionRuntime:
    """Fan-out processor: every event is delivered to every registered component.

    Attach Count-Min, Space-Saving, exporters, or future window operators
    through the registry. The runtime never imports a concrete sketch, so
    new algorithms can be added without changing this module.
    """

    def __init__(self, components: Iterable[Component] | None = None) -> None:
        self.registry = ComponentRegistry()
        self.context = ComponentContext()
        if components:
            for component in components:
                self.attach(component)

    def attach(self, component: Component, *, replace: bool = False) -> None:
        self.registry.register(component, replace=replace)
        component.configure(self.context)

    def ingest(self, key, weight: int = 1, **attributes) -> None:
        self.push(StreamEvent(key=key, weight=weight, attributes=attributes))

    def push(self, event: StreamEvent) -> None:
        self.context.total_events += event.weight
        for component in self.registry:
            component.on_event(event, self.context)

    def extend(self, events: Iterable[StreamEvent]) -> None:
        for event in events:
            self.push(event)

    def snapshots(self) -> Mapping[str, Mapping[str, object]]:
        return {component.name: dict(component.snapshot()) for component in self.registry}

    def close(self) -> None:
        for component in self.registry:
            component.close()
