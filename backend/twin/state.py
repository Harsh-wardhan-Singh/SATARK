from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

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

    State categories:

        entities
            Physical and human entities in the Digital Twin.

        environment
            Structured environmental/disaster state.

        metrics
            Numeric simulation measurements.

        events
            Chronological simulation events.
    """

    entities: Dict[str, Entity] = field(
        default_factory=dict
    )

    simulation_time: float = 0.0

    current_tick: int = 0

    active_calamity: Optional[CalamityType] = None

    environment: Dict[str, Any] = field(
        default_factory=dict
    )

    metrics: Dict[str, float] = field(
        default_factory=dict
    )

    events: List[dict] = field(
        default_factory=list
    )

    def add_entity(
        self,
        entity: Entity,
    ) -> None:
        """
        Add an entity to the world.

        Entity IDs must be unique within the Digital Twin.
        """

        if entity.id in self.entities:
            raise ValueError(
                f"Entity with id '{entity.id}' already exists."
            )

        self.entities[
            entity.id
        ] = entity

    def add_entities(
        self,
        entities: Iterable[Entity],
    ) -> None:
        """
        Add multiple entities to the world.
        """

        for entity in entities:
            self.add_entity(entity)

    def remove_entity(
        self,
        entity_id: str,
    ) -> Entity:
        """
        Remove and return an entity.
        """

        try:
            return self.entities.pop(
                entity_id
            )
        except KeyError as exc:
            raise KeyError(
                f"Entity with id '{entity_id}' does not exist."
            ) from exc

    def get_entity(
        self,
        entity_id: str,
    ) -> Optional[Entity]:
        """
        Return an entity by ID.
        """

        return self.entities.get(
            entity_id
        )

    def require_entity(
        self,
        entity_id: str,
    ) -> Entity:
        """
        Return an entity by ID.

        Raises KeyError if it does not exist.
        """

        entity = self.get_entity(
            entity_id
        )

        if entity is None:
            raise KeyError(
                f"Entity with id '{entity_id}' does not exist."
            )

        return entity

    def get_entities(
        self,
    ) -> List[Entity]:
        """
        Return all entities currently present.
        """

        return list(
            self.entities.values()
        )

    def update_entity_position(
        self,
        entity_id: str,
        position: Position,
    ) -> None:
        """
        Update an entity's authoritative position.
        """

        entity = self.require_entity(
            entity_id
        )

        entity.set_position(
            position
        )

    def set_calamity(
        self,
        calamity_type: Optional[CalamityType],
    ) -> None:
        """
        Set or clear the active calamity.
        """

        self.active_calamity = (
            calamity_type
        )

    def advance_time(
        self,
        delta_time: float,
    ) -> None:
        """
        Advance authoritative simulation time.
        """

        if delta_time < 0:
            raise ValueError(
                "delta_time cannot be negative."
            )

        self.simulation_time += (
            delta_time
        )

    def record_event(
        self,
        event: dict,
    ) -> None:
        """
        Record one simulation event.
        """

        self.events.append(
            dict(event)
        )

    def update_metric(
        self,
        name: str,
        value: float,
    ) -> None:
        """
        Store one numeric simulation metric.
        """

        self.metrics[
            name
        ] = float(value)

    def clear(self) -> None:
        """
        Clear the authoritative world state.
        """

        self.entities.clear()

        self.simulation_time = 0.0

        self.current_tick = 0

        self.active_calamity = None

        self.environment.clear()

        self.metrics.clear()

        self.events.clear()