from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Iterable

from agents.manager import AgentManager
from algorithms.flood.impact import FloodImpactEngine
from algorithms.infrastructure.cascade import ExplainableNetwork
from calamities.flood import Flood
from core.enums import CalamityType
from infrastructure.facility import Facility
from twin.entity import Entity

from simulation.clock import SimulationClock
from simulation.scenario import Scenario
from simulation.world import SimulationWorld


class SimulationEngine:
    """
    Central SATARK simulation orchestrator.

    Current integrated pipeline:

        Scenario
            ↓
        Flood
            ↓
        FloodPropagator
            ↓
        FloodImpactEngine
            ↓
        zone impact scores
            ↓
        ExplainableNetwork
            ↓
        infrastructure capacity / cascade state
            ↓
        WorldState

    HumanAgent behaviour remains deterministic and is updated through
    AgentManager.

    Later phases will connect:

        panic
        evacuation
        crowd
        casualties
        risk
        decision
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

        # --------------------------------------------------------------
        # Flood
        # --------------------------------------------------------------

        self._flood: Flood | None = None

        self._flood_impact: (
            FloodImpactEngine | None
        ) = None

        self._flood_zone_data: (
            dict[str, dict[str, Any]]
        ) = {}

        # --------------------------------------------------------------
        # Infrastructure cascade
        # --------------------------------------------------------------

        self._infrastructure_network: (
            ExplainableNetwork | None
        ) = None

        self._infrastructure_state: (
            dict[str, dict[str, Any]]
        ) = {}

        self._initialized = False
        self._paused = False

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self):
        """
        Return the authoritative Digital Twin WorldState.
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

    @property
    def flood(self) -> Flood | None:
        """
        Return the active Flood calamity.
        """

        return self._flood

    @property
    def infrastructure_state(
        self,
    ) -> dict[str, dict[str, Any]]:
        """
        Return the latest infrastructure state.

        A copy is returned so external callers cannot directly mutate
        the engine's internal cascade state.
        """

        return {
            node_id: dict(state)
            for node_id, state
            in self._infrastructure_state.items()
        }

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Initialize the Digital Twin and configured calamity.
        """

        self.clock.reset()

        self.world.initialize(
            entities=self._initial_entities,
            calamity_type=(
                self.scenario.calamity_type
            ),
        )

        self._agent_manager = AgentManager(
            self.world.state
        )

        self._initialize_calamity()

        self._sync_world_time()

        self.world.state.record_event(
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

    def _initialize_calamity(self) -> None:
        """
        Initialize the configured hazard subsystem.

        Phase 9 currently integrates Flood.

        Earthquake will be connected in a later phase.

        Tsunami is intentionally not part of SATARK.
        """

        if (
            self.scenario.calamity_type
            == CalamityType.FLOOD
        ):
            self._initialize_flood()
            return

        if (
            self.scenario.calamity_type
            == CalamityType.EARTHQUAKE
        ):
            raise NotImplementedError(
                "Earthquake simulation integration "
                "will be implemented in a later phase."
            )

        raise ValueError(
            "Unsupported calamity type: "
            f"{self.scenario.calamity_type}"
        )

    def _initialize_flood(self) -> None:
        """
        Initialize the existing FloodPropagator and infrastructure
        cascade algorithms.
        """

        # --------------------------------------------------------------
        # Zone mapping
        # --------------------------------------------------------------

        zone_mapping_path = (
            self.scenario.zone_mapping_path
        )

        if not zone_mapping_path:
            raise ValueError(
                "Flood scenarios require the "
                "'zone_mapping_path' parameter."
            )

        mapping_path = Path(
            zone_mapping_path
        )

        if not mapping_path.exists():
            raise FileNotFoundError(
                "Flood zone mapping file not found: "
                f"{mapping_path}"
            )

        # --------------------------------------------------------------
        # Flood propagation
        # --------------------------------------------------------------

        self._flood = Flood(
            zone_mapping_path=mapping_path,
            rainfall_intensity=(
                self.scenario.rainfall_intensity
            ),
            model_step_seconds=(
                self.scenario
                .flood_model_step_seconds
            ),
        )

        self._flood.initialize()

        self._flood_zone_data = {
            zone["id"]: zone
            for zone in (
                self._flood
                .propagator
                .zone_data
            )
        }

        # --------------------------------------------------------------
        # Flood ML
        # --------------------------------------------------------------

        self._flood_impact = (
            FloodImpactEngine()
        )

        # --------------------------------------------------------------
        # Infrastructure cascade
        # --------------------------------------------------------------

        infrastructure_path = (
            self.scenario.infrastructure_path
        )

        if not infrastructure_path:
            raise ValueError(
                "Flood scenarios require the "
                "'infrastructure_path' parameter."
            )

        infrastructure_file = Path(
            infrastructure_path
        )

        if not infrastructure_file.exists():
            raise FileNotFoundError(
                "Infrastructure data file not found: "
                f"{infrastructure_file}"
            )

        self._infrastructure_network = (
            ExplainableNetwork(
                str(infrastructure_file)
            )
        )

        self._infrastructure_state = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def pause(self) -> None:
        """
        Pause simulation progression.
        """

        self._paused = True

    def resume(self) -> None:
        """
        Resume simulation progression.
        """

        if not self._initialized:
            raise RuntimeError(
                "Simulation must be initialized "
                "before resuming."
            )

        self._paused = False

    def reset(self) -> None:
        """
        Reset the entire simulation engine.
        """

        self.clock.reset()

        if self._flood is not None:
            self._flood.reset()

        self.world.reset()

        self._agent_manager = None

        self._flood = None

        self._flood_impact = None

        self._flood_zone_data = {}

        self._infrastructure_network = None

        self._infrastructure_state = {}

        self._initialized = False

        self._paused = False

    # ------------------------------------------------------------------
    # Simulation progression
    # ------------------------------------------------------------------

    def step(self) -> None:
        """
        Advance the simulation by exactly one simulation tick.
        """

        if not self._initialized:
            self.initialize()

        if self._paused:
            raise RuntimeError(
                "Simulation is paused."
            )

        if self.is_complete:
            raise RuntimeError(
                "Simulation duration has already "
                "been reached."
            )

        delta_time = (
            self.clock.advance()
        )

        self._sync_world_time()

        # --------------------------------------------------------------
        # 1. Disaster
        # --------------------------------------------------------------

        self._step_calamity(
            delta_time
        )

        # --------------------------------------------------------------
        # 2. Human agents
        # --------------------------------------------------------------

        self._update_agents(
            delta_time
        )

        # --------------------------------------------------------------
        # 3. Basic metrics
        # --------------------------------------------------------------

        self._update_basic_metrics()

        self.world.state.record_event(
            {
                "type": "SIMULATION_TICK",
                "tick": self.clock.current_tick,
            }
        )

    # ------------------------------------------------------------------
    # Calamity progression
    # ------------------------------------------------------------------

    def _step_calamity(
        self,
        delta_time: float,
    ) -> None:
        """
        Advance the active calamity.
        """

        if (
            self.scenario.calamity_type
            == CalamityType.FLOOD
        ):
            self._step_flood(
                delta_time
            )

    def _step_flood(
        self,
        delta_time: float,
    ) -> None:
        """
        Advance flood propagation, calculate ML impact, and then
        calculate infrastructure cascade.
        """

        if self._flood is None:
            raise RuntimeError(
                "Flood calamity has not been initialized."
            )

        if self._flood_impact is None:
            raise RuntimeError(
                "Flood impact engine has not been initialized."
            )

        if self._infrastructure_network is None:
            raise RuntimeError(
                "Infrastructure cascade network "
                "has not been initialized."
            )

        # --------------------------------------------------------------
        # Flood propagation
        # --------------------------------------------------------------

        flood_state = self._flood.step(
            delta_time
        )

        water_levels = flood_state[
            "water_levels"
        ]

        # --------------------------------------------------------------
        # Environment state
        # --------------------------------------------------------------

        self.world.state.environment[
            "rainfall_intensity"
        ] = (
            self.scenario.rainfall_intensity
        )

        self.world.state.environment[
            "flood_water_levels"
        ] = dict(
            water_levels
        )

        # --------------------------------------------------------------
        # Numeric flood metrics
        # --------------------------------------------------------------

        for zone_id, water_level in (
            water_levels.items()
        ):
            self.world.state.update_metric(
                f"flood_water_{zone_id}",
                float(
                    water_level
                ),
            )

        # --------------------------------------------------------------
        # ML impact
        # --------------------------------------------------------------

        day = max(
            1,
            int(
                self.clock.simulation_time
                / 86400.0
            ) + 1,
        )

        impact_scores = (
            self._flood_impact.calculate_impacts(
                water_levels,
                self._flood_zone_data,
                severity=self.scenario.severity,
                day=day,
                intervention_level=(
                    self.scenario
                    .intervention_level
                ),
            )
        )

        self.world.state.environment[
            "flood_impact_scores"
        ] = dict(
            impact_scores
        )

        for zone_id, impact in (
            impact_scores.items()
        ):
            self.world.state.update_metric(
                f"flood_impact_{zone_id}",
                float(
                    impact
                ),
            )

        # --------------------------------------------------------------
        # Infrastructure cascade
        # --------------------------------------------------------------

        self._step_infrastructure(
            impact_scores
        )

        # --------------------------------------------------------------
        # Record combined flood update
        # --------------------------------------------------------------

        self.world.state.record_event(
            {
                "type": "FLOOD_STATE_UPDATED",
                "tick": self.clock.current_tick,
                "water_levels": dict(
                    water_levels
                ),
                "impact_scores": dict(
                    impact_scores
                ),
            }
        )

    # ------------------------------------------------------------------
    # Infrastructure cascade
    # ------------------------------------------------------------------

    def _step_infrastructure(
        self,
        impact_scores: dict[str, float],
    ) -> None:
        """
        Run the existing ExplainableNetwork infrastructure cascade.

        Input:
            zone_id -> flood impact score

        Output:
            Infrastructure capacity and explanation state.

        The cascade mathematics remains inside
        algorithms/infrastructure/cascade.py.
        """

        if (
            self._infrastructure_network
            is None
        ):
            raise RuntimeError(
                "Infrastructure cascade network "
                "has not been initialized."
            )

        # --------------------------------------------------------------
        # Run friend's existing algorithm.
        # --------------------------------------------------------------

        self._infrastructure_network.simulate_timestep(
            impact_scores
        )

        infrastructure_state: dict[
            str,
            dict[str, Any],
        ] = {}

        # --------------------------------------------------------------
        # Extract current algorithm state.
        # --------------------------------------------------------------

        for node_id, node in (
            self._infrastructure_network
            .nodes
            .items()
        ):

            capacity = float(
                node.get(
                    "capacity",
                    1.0,
                )
            )

            reason = str(
                node.get(
                    "status_reason",
                    "Unknown",
                )
            )

            node_state = {
                "id": node_id,
                "name": node.get(
                    "name",
                    node_id,
                ),
                "type": node.get(
                    "type",
                    "UNKNOWN",
                ),
                "zone_id": node.get(
                    "zone_id"
                ),
                "capacity": capacity,
                "status_reason": reason,
            }

            infrastructure_state[
                node_id
            ] = node_state

            # ----------------------------------------------------------
            # Numeric metrics
            # ----------------------------------------------------------

            self.world.state.update_metric(
                f"infrastructure_capacity_{node_id}",
                capacity,
            )

        # --------------------------------------------------------------
        # Store structured authoritative infrastructure state.
        # --------------------------------------------------------------

        self._infrastructure_state = (
            infrastructure_state
        )

        self.world.state.environment[
            "infrastructure"
        ] = {
            node_id: dict(state)
            for node_id, state
            in infrastructure_state.items()
        }

        # --------------------------------------------------------------
        # Record infrastructure event.
        # --------------------------------------------------------------

        self.world.state.record_event(
            {
                "type": (
                    "INFRASTRUCTURE_STATE_UPDATED"
                ),
                "tick": self.clock.current_tick,
                "infrastructure": {
                    node_id: dict(state)
                    for node_id, state
                    in infrastructure_state.items()
                },
            }
        )

    # ------------------------------------------------------------------
    # Existing agent subsystem
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

        self.world.state.update_metric(
            "agent_count",
            float(
                len(agents)
            ),
        )

        self.world.state.update_metric(
            "normal_agents",
            float(
                len(
                    self._agent_manager
                    .get_normal_agents()
                )
            ),
        )

        self.world.state.update_metric(
            "panicked_agents",
            float(
                len(
                    self._agent_manager
                    .get_panicked_agents()
                )
            ),
        )

        self.world.state.update_metric(
            "safe_agents",
            float(
                len(
                    self._agent_manager
                    .get_safe_agents()
                )
            )
        )