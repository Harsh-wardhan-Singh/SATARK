from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from core.enums import CalamityType
from core.types import Position

from twin.entity import Entity


@dataclass
class WorldState:
    """
    Authoritative in-memory state of the SATARK Digital Twin.

    WorldState represents the current condition of the simulated world.
    It does not execute simulation logic and does not persist data to a
    database.
    """

    entities: Dict[str, Entity] = field(default_factory=dict)

    simulation_time: float = 0.0

    current_tick: int = 0

    active_calamity: Optional[CalamityType] = None

    environment: Dict[str, float] = field(default_factory=dict)

    metrics: Dict[str, float] = field(default_factory=dict)

    events: List[dict] = field(default_factory=list)

    def add_entity(self, entity: Entity) -> None:
        """
        Add an entity to the world.

        Entity IDs must be unique within the Digital Twin.
        """
        if entity.id in self.entities:
            raise ValueError(
                f"Entity with id '{entity.id}' already exists."
            )

        self.entities[entity.id] = entity

    def add_entities(self, entities: Iterable[Entity]) -> None:
        """
        Add multiple entities to the world.
        """
        for entity in entities:
            self.add_entity(entity)

    def remove_entity(self, entity_id: str) -> Entity:
        """
        Remove and return an entity from the world.
        """
        try:
            return self.entities.pop(entity_id)
        except KeyError as exc:
            raise KeyError(
                f"Entity with id '{entity_id}' does not exist."
            ) from exc

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """
        Return an entity by ID.

        Returns None if the entity does not exist.
        """
        return self.entities.get(entity_id)

    def require_entity(self, entity_id: str) -> Entity:
        """
        Return an entity by ID.

        Raises KeyError if the entity does not exist.
        """
        entity = self.get_entity(entity_id)

        if entity is None:
            raise KeyError(
                f"Entity with id '{entity_id}' does not exist."
            )

        return entity

    def get_entities(self) -> List[Entity]:
        """
        Return all entities currently present in the world.
        """
        return list(self.entities.values())

    def update_entity_position(
        self,
        entity_id: str,
        position: Position,
    ) -> None:
        """
        Update an entity's position inside the authoritative world state.
        """
        entity = self.require_entity(entity_id)
        entity.set_position(position)

    def set_calamity(
        self,
        calamity_type: Optional[CalamityType],
    ) -> None:
        """
        Set or clear the active calamity.
        """
        self.active_calamity = calamity_type

    def advance_time(
        self,
        delta_time: float,
    ) -> None:
        """
        Advance simulation time.

        WorldState stores the time; the SimulationClock will later be
        responsible for determining how much time should advance.
        """
        if delta_time < 0:
            raise ValueError("delta_time cannot be negative.")

        self.simulation_time += delta_time
        self.current_tick += 1

    def record_event(self, event: dict) -> None:
        """
        Record a simulation event.
        """
        self.events.append(event)

    def update_metric(
        self,
        name: str,
        value: float,
    ) -> None:
        """
        Store or update a world-level metric.
        """
        self.metrics[name] = value

    def clear(self) -> None:
        """
        Reset the world state to an empty initial state.
        """
        self.entities.clear()
        self.simulation_time = 0.0
        self.current_tick = 0
        self.active_calamity = None
        self.environment.clear()
        self.metrics.clear()
        self.events.clear()
