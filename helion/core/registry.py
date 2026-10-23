from __future__ import annotations

from collections.abc import Iterator

from helion.core.component import Component


class ComponentRegistry:
    def __init__(self) -> None:
        self._components: dict[str, Component] = {}

    def register(self, component: Component, *, replace: bool = False) -> None:
        name = component.name
        if not name:
            raise ValueError("component name must be non-empty")
        if name in self._components and not replace:
            raise KeyError(f"component already registered: {name}")
        self._components[name] = component

    def get(self, name: str) -> Component:
        try:
            return self._components[name]
        except KeyError:
            raise KeyError(f"unknown component: {name}") from None

    def contains(self, name: str) -> bool:
        return name in self._components

    def names(self) -> list[str]:
        return list(self._components.keys())

    def as_list(self) -> list[Component]:
        return list(self._components.values())

    def __iter__(self) -> Iterator[Component]:
        return iter(self._components.values())

    def __len__(self) -> int:
        return len(self._components)
