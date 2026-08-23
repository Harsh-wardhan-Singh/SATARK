from typing import Iterable, Optional

from core.enums import CalamityType
from twin.entity import Entity
from twin.manager import TwinManager
from twin.state import WorldState
from twin.twin import DigitalTwin

from simulation.scenario import Scenario


class SimulationWorld:
    """
    Simulation-facing wrapper around the authoritative Digital Twin.

    SimulationWorld does not maintain a separate WorldState.

    The DigitalTwin owned by this object contains the authoritative
    WorldState for the simulation.
    """

    def __init__(
        self,
        twin_manager: Optional[TwinManager] = None,
    ) -> None:
        self.twin_manager = twin_manager or TwinManager()
        self.twin: Optional[DigitalTwin] = None

    @property
    def world_state(self) -> WorldState:
        """
        Return the authoritative WorldState.

        Raises:
            RuntimeError: if the simulation world has not been initialized.
        """
        if self.twin is None:
            raise RuntimeError(
                "SimulationWorld has not been initialized."
            )

        return self.twin.world_state

    def initialize(
        self,
        scenario: Scenario,
    ) -> DigitalTwin:
        """
        Create and initialize the Digital Twin from a Scenario.
        """
        self.twin = self.twin_manager.initialize_twin(
            entities=scenario.get_initial_entities()
        )

        self.world_state.environment.update(
            scenario.get_initial_environment()
        )

        self.world_state.set_calamity(
            scenario.calamity_type
        )

        self.world_state.record_event(
            {
                "type": "SIMULATION_INITIALIZED",
                "calamity": scenario.calamity_type.value,
            }
        )

        return self.twin

    def add_entity(self, entity: Entity) -> None:
        """
        Add an entity to the authoritative Digital Twin.
        """
        self._require_initialized().add_entity(entity)

    def add_entities(
        self,
        entities: Iterable[Entity],
    ) -> None:
        """
        Add multiple entities to the authoritative Digital Twin.
        """
        self._require_initialized().add_entities(entities)

    def set_calamity(
        self,
        calamity_type: Optional[CalamityType],
    ) -> None:
        """
        Update the active calamity in the authoritative WorldState.
        """
        self.world_state.set_calamity(calamity_type)

    def advance_time(
        self,
        delta_time: float,
    ) -> None:
        """
        Advance the authoritative WorldState by the supplied time step.
        """
        self.world_state.advance_time(delta_time)

    def reset(self) -> None:
        """
        Reset the active Digital Twin.
        """
        if self.twin is None:
            return

        self.twin_manager.reset_twin()

    def _require_initialized(self) -> DigitalTwin:
        """
        Return the active Digital Twin or raise a clear error.
        """
        if self.twin is None:
            raise RuntimeError(
                "SimulationWorld has not been initialized."
            )

        return self.twin