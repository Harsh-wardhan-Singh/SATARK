from typing import Iterable, Optional

from twin.entity import Entity
from twin.state import WorldState


class DigitalTwin:
    """
    Central in-memory representation of the SATARK simulated world.

    DigitalTwin owns the authoritative WorldState but does not itself
    execute simulation, prediction, optimization, or decision logic.
    """

    def __init__(self, world_state: Optional[WorldState] = None) -> None:
        self._world_state = world_state or WorldState()

    @property
    def world_state(self) -> WorldState:
        """
        Return the authoritative current world state.
        """
        return self._world_state

    def add_entity(self, entity: Entity) -> None:
        """
        Add an entity to the Digital Twin.
        """
        self._world_state.add_entity(entity)

    def add_entities(self, entities: Iterable[Entity]) -> None:
        """
        Add multiple entities to the Digital Twin.
        """
        self._world_state.add_entities(entities)

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """
        Retrieve an entity by ID.
        """
        return self._world_state.get_entity(entity_id)

    def remove_entity(self, entity_id: str) -> Entity:
        """
        Remove an entity from the Digital Twin.
        """
        return self._world_state.remove_entity(entity_id)

    def reset(self) -> None:
        """
        Reset the Digital Twin to an empty initial world.
        """
        self._world_state.clear()

    def entity_count(self) -> int:
        """
        Return the number of entities currently represented.
        """
        return len(self._world_state.entities)
