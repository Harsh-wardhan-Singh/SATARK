from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Iterable, Mapping

from agents.manager import AgentManager

from algorithms.casualties.estimation import CasualtiesEngine
from algorithms.flood.impact import FloodImpactEngine
from algorithms.infrastructure.cascade import ExplainableNetwork
from algorithms.population.crowd import CrowdDynamicsEngine
from algorithms.population.evacuation import EvacuationEngine
from algorithms.population.panic import PanicEngine

from calamities.flood import Flood

from core.enums import CalamityType
from infrastructure.facility import Facility
from risk.risk_engine import RiskAssessment, RiskEngine
from twin.entity import Entity

from simulation.clock import SimulationClock
from simulation.scenario import Scenario
from simulation.world import SimulationWorld


class SimulationEngine:
    """
    Central SATARK simulation orchestrator.

    Current integrated execution order:

        Scenario
            ↓
        Flood
            ↓
        FloodImpactEngine
            ↓
        ExplainableNetwork
            ↓
        PanicEngine
            ↓
        EvacuationEngine
            ↓
        CrowdDynamicsEngine
            ↓
        CasualtiesEngine
            ↓
        RiskEngine
            ↓
        HumanAgent
            ↓
        WorldState

    The individual algorithms remain authoritative in their respective
    algorithm modules.

    SimulationEngine is responsible only for orchestration and for
    transferring authoritative state between subsystems.

    Risk is calculated from actual simulation outputs.

    It does not:
        - duplicate risk mathematics
        - invent risk values
        - modify the Digital Twin directly from the risk algorithm
        - perform optimization
        - generate recommendations
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

        # --------------------------------------------------------------
        # Agent manager
        # --------------------------------------------------------------

        self._agent_manager: (
            AgentManager | None
        ) = None

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

        # --------------------------------------------------------------
        # Human response
        # --------------------------------------------------------------

        self._panic_engine: (
            PanicEngine | None
        ) = None

        self._evacuation_engine: (
            EvacuationEngine | None
        ) = None

        self._crowd_engine: (
            CrowdDynamicsEngine | None
        ) = None

        self._casualties_engine: (
            CasualtiesEngine | None
        ) = None

        self._panic_state: dict[
            str,
            float,
        ] = {}

        self._evacuation_routes: dict[
            str,
            Any,
        ] = {}

        self._crowd_state: dict[
            str,
            Any,
        ] = {}

        self._casualty_state: dict[
            str,
            Any,
        ] = {}

        self._population_data: (
            Mapping[str, Any] | None
        ) = None

        self._shelter_data: (
            Mapping[str, Any] | None
        ) = None

        self._human_response_enabled = False

        self._panic_accumulator = 0.0

        self._population_model_step_seconds = 1.0

        self._panic_threshold = 0.5

        # --------------------------------------------------------------
        # Risk
        # --------------------------------------------------------------

        self._risk_engine: RiskEngine = (
            RiskEngine()
        )

        self._risk_assessment: (
            RiskAssessment | None
        ) = None

        self._risk_state: dict[str, Any] = {}

        # --------------------------------------------------------------
        # Lifecycle
        # --------------------------------------------------------------

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
        """

        return {
            node_id: dict(
                node_state
            )
            for node_id, node_state
            in self._infrastructure_state.items()
        }

    @property
    def panic_state(
        self,
    ) -> dict[str, float]:
        """
        Return the latest zone-level panic state.
        """

        return dict(
            self._panic_state
        )

    @property
    def evacuation_routes(
        self,
    ) -> dict[str, Any]:
        """
        Return the latest zone-level evacuation routes.
        """

        return dict(
            self._evacuation_routes
        )

    @property
    def crowd_state(
        self,
    ) -> dict[str, Any]:
        """
        Return the latest crowd state.
        """

        return dict(
            self._crowd_state
        )

    @property
    def casualty_state(
        self,
    ) -> dict[str, Any]:
        """
        Return the latest casualty state.
        """

        return dict(
            self._casualty_state
        )

    @property
    def risk_assessment(
        self,
    ) -> RiskAssessment | None:
        """
        Return the latest structured RiskAssessment.
        """

        return self._risk_assessment

    @property
    def risk_state(
        self,
    ) -> dict[str, Any]:
        """
        Return a JSON-compatible representation of the latest risk
        assessment.

        Returns an empty dictionary before the first risk evaluation.
        """

        return dict(
            self._risk_state
        )

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Initialize the Digital Twin and all configured simulation
        subsystems.
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

        self._initialize_human_response()

        self._initialize_calamity()

        self._initialize_risk()

        self._sync_world_time()

        self.world.state.record_event(
            {
                "type": "SIMULATION_INITIALIZED",
                "calamity": (
                    self.scenario
                    .calamity_type
                    .value
                ),
                "human_response_enabled": (
                    self._human_response_enabled
                ),
                "risk_engine_enabled": True,
            }
        )

        self._initialized = True
        self._paused = False

    # ------------------------------------------------------------------
    # Human-response initialization
    # ------------------------------------------------------------------

    def _initialize_human_response(
        self,
    ) -> None:
        """
        Initialize the population-response subsystem.

        Population and shelter data are supplied through Scenario.

        The project intentionally does not fabricate future JSON datasets.
        The final datasets will be supplied once the full system is ready.
        """

        self._panic_engine = None
        self._evacuation_engine = None
        self._crowd_engine = None
        self._casualties_engine = None

        self._panic_state = {}
        self._evacuation_routes = {}
        self._crowd_state = {}
        self._casualty_state = {}

        self._human_response_enabled = False

        self._population_data = (
            self.scenario.get_initial_state(
                "population_data"
            )
        )

        self._shelter_data = (
            self.scenario.get_initial_state(
                "shelter_data"
            )
        )

        self._panic_threshold = float(
            self.scenario.get_parameter(
                "panic_threshold",
                0.5,
            )
        )

        self._population_model_step_seconds = float(
            self.scenario.get_parameter(
                "population_model_step_seconds",
                1.0,
            )
        )

        if not 0.0 <= self._panic_threshold <= 1.0:
            raise ValueError(
                "panic_threshold must be between 0.0 and 1.0."
            )

        if self._population_model_step_seconds <= 0:
            raise ValueError(
                "population_model_step_seconds "
                "must be greater than 0."
            )

        if self._population_data is None:
            self.world.state.environment[
                "human_response"
            ] = {
                "enabled": False,
                "reason": (
                    "population_data is not configured "
                    "in Scenario.initial_state."
                ),
                "panic_by_zone": {},
                "evacuation_routes": {},
                "crowd": {},
                "casualties": {},
            }

            self.world.state.record_event(
                {
                    "type": (
                        "HUMAN_RESPONSE_WAITING_FOR_DATA"
                    ),
                    "missing": [
                        "population_data",
                    ],
                }
            )

            return

        if not isinstance(
            self._population_data,
            Mapping,
        ):
            raise TypeError(
                "population_data must be a mapping."
            )

        if "zones" not in self._population_data:
            raise ValueError(
                "population_data must contain 'zones'."
            )

        # --------------------------------------------------------------
        # Panic
        # --------------------------------------------------------------

        self._panic_engine = PanicEngine(
            self._population_data
        )

        self._panic_state = dict(
            self._panic_engine.panic_state
        )

        # --------------------------------------------------------------
        # Shelter-dependent population algorithms
        # --------------------------------------------------------------

        if self._shelter_data is None:

            self._human_response_enabled = True

            self.world.state.environment[
                "human_response"
            ] = {
                "enabled": True,
                "partial": True,
                "reason": (
                    "population_data is available, "
                    "but shelter_data is not configured."
                ),
                "panic_by_zone": dict(
                    self._panic_state
                ),
                "evacuation_routes": {},
                "crowd": {},
                "casualties": {},
            }

            return

        if not isinstance(
            self._shelter_data,
            Mapping,
        ):
            raise TypeError(
                "shelter_data must be a mapping."
            )

        if "shelters" not in self._shelter_data:
            raise ValueError(
                "shelter_data must contain 'shelters'."
            )

        zones_path = (
            self.scenario.get_parameter(
                "zones_path"
            )
        )

        shelters_path = (
            self.scenario.get_parameter(
                "shelters_path"
            )
        )

        if not zones_path or not shelters_path:
            self._human_response_enabled = True

            self.world.state.environment[
                "human_response"
            ] = {
                "enabled": True,
                "partial": True,
                "reason": (
                    "Population and shelter data are "
                    "available, but evacuation zone "
                    "and shelter paths are not configured."
                ),
                "panic_by_zone": dict(
                    self._panic_state
                ),
                "evacuation_routes": {},
                "crowd": {},
                "casualties": {},
            }

            return

        zones_file = Path(
            zones_path
        )

        shelters_file = Path(
            shelters_path
        )

        if not zones_file.exists():
            raise FileNotFoundError(
                "Evacuation zone file not found: "
                f"{zones_file}"
            )

        if not shelters_file.exists():
            raise FileNotFoundError(
                "Evacuation shelter file not found: "
                f"{shelters_file}"
            )

        # --------------------------------------------------------------
        # Evacuation
        # --------------------------------------------------------------

        self._evacuation_engine = (
            EvacuationEngine(
                zones_path=zones_file,
                shelters_path=shelters_file,
            )
        )

        # --------------------------------------------------------------
        # Crowd
        # --------------------------------------------------------------

        self._crowd_engine = (
            CrowdDynamicsEngine(
                population_data=self._population_data,
                shelter_data=self._shelter_data,
            )
        )

        # --------------------------------------------------------------
        # Casualties
        # --------------------------------------------------------------

        infrastructure_data = (
            self._build_casualty_infrastructure_data()
        )

        self._casualties_engine = (
            CasualtiesEngine(
                infrastructure_data
            )
        )

        self._human_response_enabled = True

        self.world.state.environment[
            "human_response"
        ] = {
            "enabled": True,
            "partial": False,
            "panic_threshold": (
                self._panic_threshold
            ),
            "panic_by_zone": dict(
                self._panic_state
            ),
            "evacuation_routes": {},
            "crowd": {},
            "casualties": {},
        }

    # ------------------------------------------------------------------
    # Risk initialization
    # ------------------------------------------------------------------

    def _initialize_risk(
        self,
    ) -> None:
        """
        Initialize the canonical RiskEngine.

        RiskEngine itself is stateless with respect to the Digital Twin,
        so initialization only resets the previous assessment and creates
        the initial WorldState risk container.
        """

        self._risk_engine = RiskEngine()

        self._risk_assessment = None

        self._risk_state = {}

        self.world.state.environment[
            "risk"
        ] = {
            "available": True,
            "assessment": None,
        }

    # ------------------------------------------------------------------
    # Infrastructure adapter for casualties
    # ------------------------------------------------------------------

    def _build_casualty_infrastructure_data(
        self,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Convert the authoritative infrastructure cascade state into the
        structure expected by CasualtiesEngine.
        """

        infrastructure = []

        for node_id, node_state in (
            self._infrastructure_state.items()
        ):
            infrastructure.append(
                {
                    "id": node_id,
                    "type": node_state.get(
                        "type",
                        "UNKNOWN",
                    ),
                    "zone_id": node_state.get(
                        "zone_id"
                    ),
                }
            )

        return {
            "infrastructure": infrastructure,
        }

    # ------------------------------------------------------------------
    # Calamity initialization
    # ------------------------------------------------------------------

    def _initialize_calamity(
        self,
    ) -> None:
        """
        Initialize the configured calamity subsystem.
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

    def _initialize_flood(
        self,
    ) -> None:
        """
        Initialize the canonical flood propagation and infrastructure
        cascade.
        """

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

        self._flood_impact = (
            FloodImpactEngine()
        )

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
        Reset the complete simulation state.
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

        self._panic_engine = None

        self._evacuation_engine = None

        self._crowd_engine = None

        self._casualties_engine = None

        self._panic_state = {}

        self._evacuation_routes = {}

        self._crowd_state = {}

        self._casualty_state = {}

        self._population_data = None

        self._shelter_data = None

        self._risk_engine = RiskEngine()

        self._risk_assessment = None

        self._risk_state = {}

        self._human_response_enabled = False

        self._panic_accumulator = 0.0

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
        # 2. Human response
        # --------------------------------------------------------------

        self._step_human_response(
            delta_time
        )

        # --------------------------------------------------------------
        # 3. Risk
        # --------------------------------------------------------------

        self._step_risk()

        # --------------------------------------------------------------
        # 4. Deterministic HumanAgent movement
        # --------------------------------------------------------------

        self._update_agents(
            delta_time
        )

        # --------------------------------------------------------------
        # 5. Metrics
        # --------------------------------------------------------------

        self._update_basic_metrics()

        self.world.state.record_event(
            {
                "type": "SIMULATION_TICK",
                "tick": (
                    self.clock.current_tick
                ),
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
        Execute:

            Flood
            → ML impact
            → infrastructure cascade
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

        flood_state = self._flood.step(
            delta_time
        )

        water_levels = flood_state[
            "water_levels"
        ]

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

        for zone_id, water_level in (
            water_levels.items()
        ):
            self.world.state.update_metric(
                f"flood_water_{zone_id}",
                float(
                    water_level
                ),
            )

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
                severity=(
                    self.scenario.severity
                ),
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

        self._step_infrastructure(
            impact_scores
        )

        self.world.state.record_event(
            {
                "type": "FLOOD_STATE_UPDATED",
                "tick": (
                    self.clock.current_tick
                ),
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
        impact_scores: Mapping[str, float],
    ) -> None:
        """
        Execute the canonical ExplainableNetwork infrastructure cascade.
        """

        if (
            self._infrastructure_network
            is None
        ):
            raise RuntimeError(
                "Infrastructure cascade network "
                "has not been initialized."
            )

        self._infrastructure_network.simulate_timestep(
            dict(
                impact_scores
            )
        )

        infrastructure_state: dict[
            str,
            dict[str, Any],
        ] = {}

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

            self.world.state.update_metric(
                f"infrastructure_capacity_{node_id}",
                capacity,
            )

        self._infrastructure_state = (
            infrastructure_state
        )

        self.world.state.environment[
            "infrastructure"
        ] = {
            node_id: dict(
                node_state
            )
            for node_id, node_state
            in infrastructure_state.items()
        }

        self.world.state.record_event(
            {
                "type": (
                    "INFRASTRUCTURE_STATE_UPDATED"
                ),
                "tick": (
                    self.clock.current_tick
                ),
                "infrastructure": {
                    node_id: dict(
                        node_state
                    )
                    for node_id, node_state
                    in infrastructure_state.items()
                },
            }
        )

    # ------------------------------------------------------------------
    # Phase 10 — Human response
    # ------------------------------------------------------------------

    def _step_human_response(
        self,
        delta_time: float,
    ) -> None:
        """
        Execute:

            Panic
                ↓
            Evacuation
                ↓
            Crowd
                ↓
            Casualties
        """

        if not self._human_response_enabled:
            return

        if self._panic_engine is None:
            return

        self._panic_accumulator += (
            delta_time
        )

        if (
            self._panic_accumulator
            < self._population_model_step_seconds
        ):
            return

        self._panic_accumulator = (
            self._panic_accumulator
            % self._population_model_step_seconds
        )

        # --------------------------------------------------------------
        # Authoritative flood inputs
        # --------------------------------------------------------------

        flood_states = (
            self.world.state.environment.get(
                "flood_water_levels",
                {},
            )
        )

        flood_impacts = (
            self.world.state.environment.get(
                "flood_impact_scores",
                {},
            )
        )

        if not isinstance(
            flood_states,
            Mapping,
        ):
            flood_states = {}

        if not isinstance(
            flood_impacts,
            Mapping,
        ):
            flood_impacts = {}

        # --------------------------------------------------------------
        # 1. PANIC
        # --------------------------------------------------------------

        self._panic_state = (
            self._panic_engine.update_panic(
                flood_impacts=dict(
                    flood_impacts
                ),
                infra_states=(
                    self._infrastructure_state
                ),
            )
        )

        self.world.state.environment[
            "panic_by_zone"
        ] = dict(
            self._panic_state
        )

        for zone_id, panic_level in (
            self._panic_state.items()
        ):
            self.world.state.update_metric(
                f"panic_{zone_id}",
                float(
                    panic_level
                ),
            )

        # --------------------------------------------------------------
        # 2. EVACUATION
        # --------------------------------------------------------------

        if self._evacuation_engine is not None:

            evacuation_result = (
                self._evacuation_engine
                .calculate_evacuation_routes(
                    flood_states=dict(
                        flood_states
                    ),
                    panic_states=dict(
                        self._panic_state
                    ),
                )
            )

            if (
                isinstance(
                    evacuation_result,
                    Mapping,
                )
                and evacuation_result.get(
                    "status"
                )
                == "CRITICAL"
            ):
                self._evacuation_routes = {}

            else:
                self._evacuation_routes = dict(
                    evacuation_result
                )

                if self._agent_manager is not None:
                    assigned = (
                        self._agent_manager
                        .assign_evacuation_routes(
                            self._evacuation_routes
                        )
                    )

                    self.world.state.update_metric(
                        "agents_with_evacuation_routes",
                        float(
                            assigned
                        ),
                    )

            self.world.state.environment[
                "evacuation_routes"
            ] = dict(
                self._evacuation_routes
            )

        # --------------------------------------------------------------
        # 3. HumanAgent panic transition
        # --------------------------------------------------------------

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

        transitioned = 0

        if self._agent_manager is not None:

            transitioned = (
                self._agent_manager
                .trigger_panic_for_zones(
                    panic_by_zone=(
                        self._panic_state
                    ),
                    safe_centers=safe_centers,
                    threshold=(
                        self._panic_threshold
                    ),
                )
            )

        # --------------------------------------------------------------
        # 4. CROWD
        # --------------------------------------------------------------

        if self._crowd_engine is not None:

            self._crowd_state = (
                self._crowd_engine
                .simulate_movement_step(
                    evacuation_routes=(
                        self._evacuation_routes
                    ),
                    panic_states=(
                        self._panic_state
                    ),
                )
            )

            self.world.state.environment[
                "crowd"
            ] = dict(
                self._crowd_state
            )

            bottlenecks = (
                self._crowd_state.get(
                    "bottlenecks",
                    {},
                )
            )

            if isinstance(
                bottlenecks,
                Mapping,
            ):

                self.world.state.environment[
                    "bottlenecks"
                ] = dict(
                    bottlenecks
                )

                for zone_id, value in (
                    bottlenecks.items()
                ):
                    self.world.state.update_metric(
                        f"bottleneck_{zone_id}",
                        float(
                            value
                        ),
                    )

        # --------------------------------------------------------------
        # 5. CASUALTIES
        # --------------------------------------------------------------

        if self._casualties_engine is not None:

            current_populations = (
                self._get_current_populations()
            )

            bottlenecks = (
                self._crowd_state.get(
                    "bottlenecks",
                    {},
                )
            )

            self._casualty_state = (
                self._casualties_engine
                .update_casualties(
                    current_populations=(
                        current_populations
                    ),
                    flood_states=dict(
                        flood_states
                    ),
                    bottlenecks=dict(
                        bottlenecks
                    ),
                    panic_states=dict(
                        self._panic_state
                    ),
                    infra_states=(
                        self._infrastructure_state
                    ),
                )
            )

            self.world.state.environment[
                "casualties"
            ] = dict(
                self._casualty_state
            )

            self.world.state.update_metric(
                "total_fatalities",
                float(
                    self._casualty_state.get(
                        "total_fatalities",
                        0,
                    )
                ),
            )

            self.world.state.update_metric(
                "total_injuries",
                float(
                    self._casualty_state.get(
                        "total_injuries",
                        0,
                    )
                ),
            )

        self.world.state.record_event(
            {
                "type": (
                    "HUMAN_RESPONSE_UPDATED"
                ),
                "tick": (
                    self.clock.current_tick
                ),
                "panic_by_zone": dict(
                    self._panic_state
                ),
                "evacuation_routes": dict(
                    self._evacuation_routes
                ),
                "agents_transitioned_to_panic": (
                    transitioned
                ),
                "crowd": dict(
                    self._crowd_state
                ),
                "casualties": dict(
                    self._casualty_state
                ),
            }
        )

    # ------------------------------------------------------------------
    # Population state
    # ------------------------------------------------------------------

    def _get_current_populations(
        self,
    ) -> dict[str, float]:
        """
        Return the population distribution currently maintained by
        CrowdDynamicsEngine.

        HumanAgent counts are used only as a fallback when the population
        algorithm is not available.
        """

        if self._crowd_engine is not None:

            return {
                zone_id: float(
                    population
                )
                for zone_id, population
                in self._crowd_engine
                .zone_populations
                .items()
            }

        if self._agent_manager is not None:

            return {
                zone_id: float(
                    population
                )
                for zone_id, population
                in self._agent_manager
                .get_zone_population()
                .items()
            }

        return {}

    # ------------------------------------------------------------------
    # Phase 11 — Risk
    # ------------------------------------------------------------------

    def _step_risk(
        self,
    ) -> None:
        """
        Evaluate the current system-wide risk from authoritative
        simulation outputs.

        Data flow:

            WorldState
                ↓
            RiskEngine.evaluate()
                ↓
            RiskAssessment
                ↓
            WorldState.environment["risk"]
        """

        flood_states = (
            self.world.state.environment.get(
                "flood_water_levels",
                {},
            )
        )

        bottlenecks = (
            self.world.state.environment.get(
                "bottlenecks",
                {},
            )
        )

        casualties = (
            self.world.state.environment.get(
                "casualties",
                {},
            )
        )

        infrastructure = (
            self.world.state.environment.get(
                "infrastructure",
                {},
            )
        )

        if not isinstance(
            flood_states,
            Mapping,
        ):
            flood_states = {}

        if not isinstance(
            bottlenecks,
            Mapping,
        ):
            bottlenecks = {}

        if not isinstance(
            casualties,
            Mapping,
        ):
            casualties = {}

        if not isinstance(
            infrastructure,
            Mapping,
        ):
            infrastructure = {}

        total_population = (
            self._get_base_total_population()
        )

        self._risk_assessment = (
            self._risk_engine.evaluate(
                casualties=casualties,
                infrastructure=(
                    infrastructure
                ),
                flood_states=(
                    flood_states
                ),
                bottlenecks=(
                    bottlenecks
                ),
                base_total_population=(
                    total_population
                ),
            )
        )

        self._risk_state = (
            self._risk_assessment.to_dict()
        )

        self.world.state.environment[
            "risk"
        ] = {
            "available": True,
            "assessment": dict(
                self._risk_state
            ),
        }

        self.world.state.update_metric(
            "composite_risk_score",
            float(
                self._risk_assessment
                .composite_risk_score
            ),
        )

        self.world.state.record_event(
            {
                "type": "RISK_ASSESSMENT_UPDATED",
                "tick": (
                    self.clock.current_tick
                ),
                "assessment": dict(
                    self._risk_state
                ),
            }
        )

    # ------------------------------------------------------------------
    # Base population
    # ------------------------------------------------------------------

    def _get_base_total_population(
        self,
    ) -> int:
        """
        Return the scenario's total population for risk normalization.

        Population data uses the existing algorithm schema:

            zones:
                zone_id
                resident_population_estimate

        The value is the baseline population, not the current evacuated
        population, because RiskEngine uses it to normalize casualty
        impact.
        """

        if self._population_data is None:
            return 0

        zones = self._population_data.get(
            "zones",
            [],
        )

        if not isinstance(
            zones,
            list,
        ):
            return 0

        total_population = 0

        for zone in zones:

            if not isinstance(
                zone,
                Mapping,
            ):
                continue

            population = zone.get(
                "resident_population_estimate",
                0,
            )

            try:
                total_population += int(
                    population
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

        return total_population

    # ------------------------------------------------------------------
    # Agent movement
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

    def _sync_world_time(
        self,
    ) -> None:

        self.world.state.current_tick = (
            self.clock.current_tick
        )

        self.world.state.simulation_time = (
            self.clock.simulation_time
        )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def _update_basic_metrics(
        self,
    ) -> None:

        if self._agent_manager is None:
            return

        agents = (
            self._agent_manager
            .get_agents()
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
            ),
        )

        if self._panic_state:

            self.world.state.update_metric(
                "max_panic",
                float(
                    max(
                        self._panic_state.values()
                    )
                ),
            )

        if self._casualty_state:

            self.world.state.update_metric(
                "total_fatalities",
                float(
                    self._casualty_state.get(
                        "total_fatalities",
                        0,
                    )
                ),
            )

            self.world.state.update_metric(
                "total_injuries",
                float(
                    self._casualty_state.get(
                        "total_injuries",
                        0,
                    )
                ),
            )

        if self._risk_assessment is not None:

            self.world.state.update_metric(
                "composite_risk_score",
                float(
                    self._risk_assessment
                    .composite_risk_score
                ),
            )