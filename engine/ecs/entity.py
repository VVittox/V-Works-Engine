from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterator, Optional, Type, TypeVar
from .component import Component
T = TypeVar('T', bound=Component)

@dataclass(frozen=True)
class Entity:
    id: int
    name: str = 'Entity'

class ECSWorld:

    def __init__(self) -> None:
        self._next_id = 1
        self.entities: Dict[int, Entity] = {}
        self.components: Dict[type, Dict[int, Component]] = defaultdict(dict)
        self.systems = []

    def create_entity(self, name: str='Entity') -> Entity:
        e = Entity(self._next_id, name)
        self._next_id += 1
        self.entities[e.id] = e
        return e

    def destroy_entity(self, entity: Entity) -> None:
        self.entities.pop(entity.id, None)
        for store in self.components.values():
            store.pop(entity.id, None)

    def add_component(self, entity: Entity, component: T) -> T:
        if entity.id not in self.entities:
            raise KeyError('Entity does not belong to this ECSWorld')
        self.components[type(component)][entity.id] = component
        return component

    def get_component(self, entity: Entity, component_type: Type[T]) -> Optional[T]:
        return self.components.get(component_type, {}).get(entity.id)

    def query(self, *component_types: Type[Component]) -> Iterator[tuple]:
        if not component_types:
            return iter(())
        ids = set(self.components.get(component_types[0], {}))
        for t in component_types[1:]:
            ids &= set(self.components.get(t, {}))
        for entity_id in ids:
            entity = self.entities.get(entity_id)
            if entity is not None:
                yield (entity, *(self.components[t][entity_id] for t in component_types))

    def add_system(self, system) -> None:
        self.systems.append(system)

    def update(self, delta: float) -> None:
        for system in tuple(self.systems):
            system.update(self, delta)
