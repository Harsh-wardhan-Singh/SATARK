from __future__ import annotations

from typing import Any, Iterable

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

    @property
    def world_state(self) -> WorldState:
        """
        Alias for state.
        """
        return self.twin.world_state

    def initialize(
        self,
        target: Any = None,
        *,
        entities: Iterable[Entity] | None = None,
        calamity_type: CalamityType | None = None,
        environment: dict[str, Any] | None = None,
    ) -> DigitalTwin:
        """
        Initialize the simulation world.
        """

        self.twin.reset()

        if hasattr(target, "initial_state") and hasattr(target, "calamity_type"):
            scenario = target
            initial_entities = scenario.initial_state.get("entities")
            if initial_entities:
                self.twin.add_entities(initial_entities)
            initial_env = scenario.initial_state.get("environment")
            if initial_env and isinstance(initial_env, dict):
                self.state.environment.update(initial_env)
            self.state.active_calamity = scenario.calamity_type
            return self.twin

        ent_list = target if target is not None else entities
        if ent_list is not None:
            self.twin.add_entities(
                ent_list
            )

        if environment is not None:
            self.state.environment.update(environment)

        self.state.active_calamity = (
            calamity_type
        )
        return self.twin

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