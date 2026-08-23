from __future__ import annotations

from typing import Iterable

from core.enums import CalamityType
from twin.entity import Entity
from twin.state import WorldState
from twin.twin import DigitalTwin


class SimulationWorld:
    """
    Simulation-facing wrapper around the authoritative Digital Twin.

    This class does not create a second WorldState.
    """

    def __init__(
        self,
        twin: DigitalTwin | None = None,
    ) -> None:
        self.twin = (
            twin
            if twin is not None
            else DigitalTwin()
        )

    @property
    def state(self) -> WorldState:
        """
        Return the authoritative WorldState.
        """
        return self.twin.world_state

    def initialize(
        self,
        entities: Iterable[Entity] | None = None,
        *,
        calamity_type: CalamityType | None = None,
    ) -> None:
        """
        Initialize the simulation world.
        """

        self.twin.reset()

        if entities is not None:
            self.twin.add_entities(
                entities
            )

        self.state.active_calamity = (
            calamity_type
        )

    def add_entity(
        self,
        entity: Entity,
    ) -> None:
        self.twin.add_entity(
            entity
        )

    def add_entities(
        self,
        entities: Iterable[Entity],
    ) -> None:
        self.twin.add_entities(
            entities
        )

    def get_entity(
        self,
        entity_id: str,
    ) -> Entity | None:
        return self.twin.get_entity(
            entity_id
        )

    def reset(self) -> None:
        self.twin.reset()