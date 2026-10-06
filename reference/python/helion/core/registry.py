from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence

from helion.core.component import Component


class ComponentRegistry:
    """Ordered registry so additional algorithms can be attached without
    editing Count-Min or Space-Saving modules.
    """

    def __init__(self) -> None:
        self._components: dict[str, Component] = {}
        self._order: list[str] = []

    def register(self, component: Component, *, replace: bool = False) -> None:
        name = component.name
        if not name:
            raise ValueError("component name must be non-empty")
        if name in self._components and not replace:
            raise KeyError(f"component already registered: {name}")
        if name not in self._components:
            self._order.append(name)
        self._components[name] = component

    def get(self, name: str) -> Component:
        return self._components[name]

    def names(self) -> Sequence[str]:
        return tuple(self._order)

    def as_mapping(self) -> Mapping[str, Component]:
        return dict(self._components)

    def __iter__(self) -> Iterator[Component]:
        for name in self._order:
            yield self._components[name]

    def __len__(self) -> int:
        return len(self._order)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._components
