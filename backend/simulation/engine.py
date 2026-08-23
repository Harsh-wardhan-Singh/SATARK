from __future__ import annotations

import random
from typing import Iterable

from agents.manager import AgentManager
from infrastructure.facility import Facility
from twin.entity import Entity

from simulation.clock import SimulationClock
from simulation.scenario import Scenario
from simulation.world import SimulationWorld


class SimulationEngine:
    """
    Central SATARK simulation orchestrator.

    Phase 8 responsibilities:
        - initialize the scenario
        - own simulation time
        - synchronize WorldState time
        - update existing HumanAgents
        - expose simulation lifecycle controls

    Disaster/ML/cascade/risk integrations are intentionally left to
    later phases. Existing algorithm implementations must be connected
    rather than duplicated here.
    """

    def __init__(
        self,
        scenario: Scenario,
        *,
        world: SimulationWorld | None = None,
        entities: Iterable[Entity] | None = None,
    ) -> None:

        self.scenario = scenario

        self.world = (
            world
            if world is not None
            else SimulationWorld()
        )

        self.clock = SimulationClock(
            tick_rate=scenario.tick_rate
        )

        self.random = random.Random(
            scenario.random_seed
        )

        self._initial_entities = (
            list(entities)
            if entities is not None
            else []
        )

        self._agent_manager: AgentManager | None = None

        self._initialized = False
        self._paused = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self):
        """
        Return the authoritative simulation state.
        """
        return self.world.state

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def is_complete(self) -> bool:
        return (
            self.clock.simulation_time
            >= self.scenario.duration
        )

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Initialize the Digital Twin for the scenario.
        """

        self.clock.reset()

        self.world.initialize(
            entities=self._initial_entities,
            calamity_type=self.scenario.calamity_type,
        )

        self._agent_manager = AgentManager(
            self.world.state
        )

        self._sync_world_time()

        self.world.state.events.append(
            {
                "type": "SIMULATION_INITIALIZED",
                "calamity": (
                    self.scenario
                    .calamity_type
                    .value
                ),
            }
        )

        self._initialized = True
        self._paused = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        if not self._initialized:
            raise RuntimeError(
                "Simulation must be initialized before resuming."
            )

        self._paused = False

    def reset(self) -> None:
        self.clock.reset()
        self.world.reset()

        self._agent_manager = None

        self._initialized = False
        self._paused = False

    # ------------------------------------------------------------------
    # Simulation progression
    # ------------------------------------------------------------------

    def step(self) -> None:
        """
        Advance the simulation by exactly one tick.
        """

        if not self._initialized:
            self.initialize()

        if self._paused:
            raise RuntimeError(
                "Simulation is paused."
            )

        if self.is_complete:
            raise RuntimeError(
                "Simulation duration has already been reached."
            )

        delta_time = self.clock.advance()

        self._sync_world_time()

        self._update_agents(
            delta_time
        )

        self._update_basic_metrics()

        self.world.state.events.append(
            {
                "type": "SIMULATION_TICK",
                "tick": self.clock.current_tick,
            }
        )

    def run(self) -> None:
        """
        Run the simulation until its configured duration.
        """

        if not self._initialized:
            self.initialize()

        while not self.is_complete:
            self.step()

    # ------------------------------------------------------------------
    # Existing agent subsystem integration
    # ------------------------------------------------------------------

    def _update_agents(
        self,
        delta_time: float,
    ) -> None:

        if self._agent_manager is None:
            return

        safe_centers = [
            entity
            for entity in (
                self.world.state.get_entities()
            )
            if isinstance(
                entity,
                Facility,
            )
            and entity.is_safe_center
            and entity.is_operational
            and entity.available_capacity > 0
        ]

        self._agent_manager.update_all(
            delta_time=delta_time,
            safe_centers=safe_centers,
        )

    # ------------------------------------------------------------------
    # World synchronization
    # ------------------------------------------------------------------

    def _sync_world_time(self) -> None:
        self.world.state.current_tick = (
            self.clock.current_tick
        )

        self.world.state.simulation_time = (
            self.clock.simulation_time
        )

    def _update_basic_metrics(self) -> None:
        if self._agent_manager is None:
            return

        agents = (
            self._agent_manager.get_agents()
        )

        self.world.state.metrics[
            "agent_count"
        ] = float(len(agents))

        self.world.state.metrics[
            "normal_agents"
        ] = float(
            len(
                self._agent_manager
                .get_normal_agents()
            )
        )

        self.world.state.metrics[
            "panicked_agents"
        ] = float(
            len(
                self._agent_manager
                .get_panicked_agents()
            )
        )

        self.world.state.metrics[
            "safe_agents"
        ] = float(
            len(
                self._agent_manager
                .get_safe_agents()
            )
        )