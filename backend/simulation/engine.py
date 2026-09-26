from __future__ import annotations

import json
import random
from copy import deepcopy
from dataclasses import is_dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping

import logging
from agents.manager import AgentManager

from algorithms.casualties.estimation import CasualtiesEngine
from algorithms.flood.impact import FloodImpactEngine
from algorithms.drainage import (
    CoupledDrainageModel,
    DrainageNetwork,
)
from algorithms.infrastructure.cascade import ExplainableNetwork
from algorithms.population.crowd import CrowdDynamicsEngine
from algorithms.population.evacuation import EvacuationEngine
from algorithms.population.panic import PanicEngine
from algorithms.intervention.recommendations import (
    InterventionRuleEngine,
    RecommendationEngine as AlgorithmRecommendationEngine,
)
from algorithms.rainfall import (
    HyetographEngine,
    HyetographType,
    NowcastEngine,
)

from calamities.flood import Flood

from core.enums import CalamityType
from infrastructure.facility import Facility
from risk.risk_engine import RiskAssessment, RiskEngine

from decision.recommendation import (
    Recommendation,
    RecommendationEngine,
)

from twin.entity import Entity

from simulation.clock import SimulationClock
from simulation.scenario import Scenario
from simulation.world import SimulationWorld
from decision.intervention import (
    CandidateIntervention,
    Intervention,
)

from decision.optimizer import (
    OptimizationEngine,
    OptimizationResult,
    SimulationEvaluation,
)

from simulation.initialization.population import PopulationInitializer
from simulation.initialization.calamity_init import CalamityInitializer
from simulation.initialization.decision_init import DecisionInitializer
from simulation.evaluation import SimulationEvaluator

from simulation.pipeline import (
    SimulationPipeline,
    SimulationStep,
    StepContext,
    RainfallStep,
    DrainageStep,
    SurfaceFloodStep,
    FloodImpactStep,
    InfrastructureCascadeStep,
    HumanEvacuationStep,
    RiskAssessmentStep,
    DecisionInterventionStep,
    MetricsStep,
)

logger = logging.getLogger(__name__)

class SimulationEngine:
    """
    Central SATARK simulation orchestrator.

    Integrated execution order:

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
        Decision / Priority
            ↓
        Recommendation
            ↓
        Optional Scenario Intervention
            ↓
        WorldState

    The individual algorithms remain authoritative in their respective
    algorithm modules.

    SimulationEngine owns orchestration and state transfer only.

    Decision logic does not duplicate the existing algorithms.
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
            else list(scenario.initial_state.get("entities", []))
        )

        # --------------------------------------------------------------
        # Agents
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
        # Optimization
        # --------------------------------------------------------------

        self._optimization_engine = (
            OptimizationEngine(
                simulation_provider=(
                    self._provide_simulation_evaluation
                )
            )
        )

        self._optimization_result: (
            OptimizationResult | None
        ) = None

        # --------------------------------------------------------------
        # Infrastructure
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

        self._casualty_population_reduction: dict[
            str,
            float,
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

        self._risk_engine = RiskEngine()

        self._risk_assessment: (
            RiskAssessment | None
        ) = None

        self._risk_state: dict[
            str,
            Any,
        ] = {}

        # --------------------------------------------------------------
        # Decision
        # --------------------------------------------------------------

        self._algorithm_recommendation_engine = (
            AlgorithmRecommendationEngine()
        )

        self._recommendation_engine = (
            RecommendationEngine()
        )

        self._priority_state: dict[
            str,
            Any,
        ] = {}

        self._recommendations: list[
            Recommendation
        ] = []

        self._active_interventions: list[dict[str, Any]] = []

        self._cached_zone_mapping: (
            dict[str, dict[str, Any]] | None
        ) = None

        self._pipeline: (
            SimulationPipeline | None
        ) = None

        self._drainage_model: (
            CoupledDrainageModel | None
        ) = None

        self._drainage_state: dict[
            str,
            Any,
        ] = {}

        self._hyetograph: (
            HyetographEngine | None
        ) = None

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
    def is_initialized(
        self,
    ) -> bool:
        return self._initialized

    @property
    def is_paused(
        self,
    ) -> bool:
        return self._paused

    @property
    def is_complete(
        self,
    ) -> bool:
        return (
            self.clock.simulation_time
            >= self.scenario.duration
        )

    @property
    def is_finished(
        self,
    ) -> bool:
        return self.is_complete

    def run_until_complete(
        self,
    ) -> None:
        while not self.is_complete:
            self.step()

    @property
    def pipeline(
        self,
    ) -> SimulationPipeline | None:
        return self._pipeline

    @property
    def flood(
        self,
    ) -> Flood | None:
        return self._flood

    @property
    def drainage_model(
        self,
    ) -> CoupledDrainageModel | None:
        return self._drainage_model

    @property
    def drainage_state(
        self,
    ) -> dict[str, Any]:
        return dict(self._drainage_state)

    @property
    def hyetograph(
        self,
    ) -> HyetographEngine | None:
        return self._hyetograph

    @property
    def flood_zone_data(
        self,
    ) -> dict[str, dict[str, Any]]:
        return dict(self._flood_zone_data)

    def generate_nowcast(
        self,
        horizons_hours: Sequence[float] = (1.0, 2.0, 3.0),
    ) -> dict[str, Any]:
        """
        Generate forward flood projections for 0-3 hour horizons.
        """
        if self._flood is None or self._flood.propagator is None:
            raise RuntimeError(
                "Cannot generate nowcast: flood simulation is not initialized."
            )

        nowcast_engine = NowcastEngine(
            propagator=self._flood.propagator,
            hyetograph=self._hyetograph,
        )
        return nowcast_engine.generate_nowcast(
            current_simulation_time=self.clock.simulation_time,
            horizons_hours=horizons_hours,
        )

    @property
    def infrastructure_state(
        self,
    ) -> dict[
        str,
        dict[str, Any],
    ]:
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
    ) -> dict[
        str,
        float,
    ]:
        return dict(
            self._panic_state
        )

    @property
    def evacuation_routes(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return dict(
            self._evacuation_routes
        )

    @property
    def crowd_state(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return dict(
            self._crowd_state
        )

    @property
    def casualty_state(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return dict(
            self._casualty_state
        )

    @property
    def risk_assessment(
        self,
    ) -> RiskAssessment | None:
        return self._risk_assessment

    @property
    def risk_state(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return dict(
            self._risk_state
        )

    @property
    def priority_state(
        self,
    ) -> dict[
        str,
        Any,
    ]:
        return dict(
            self._priority_state
        )

    @property
    def recommendations(
        self,
    ) -> list[
        Recommendation
    ]:
        return list(
            self._recommendations
        )

    @property
    def recommendation_state(
        self,
    ) -> list[
        dict[str, Any]
    ]:
        return [
            recommendation.to_dict()
            for recommendation
            in self._recommendations
        ]

    @property
    def active_interventions(self) -> list[dict[str, Any]]:
        return [dict(i) for i in self._active_interventions]

    @property
    def active_intervention(self) -> dict[str, Any] | None:
        if not self._active_interventions:
            return None
        return dict(self._active_interventions[-1])

    @property
    def optimization_result(
        self,
    ) -> OptimizationResult | None:
        """
        Return the latest baseline-vs-intervention optimization result.
        """

        return self._optimization_result

    @property
    def optimization_state(
        self,
    ) -> dict[str, Any] | None:
        """
        Return the latest optimization result as serializable state.
        """

        if self._optimization_result is None:
            return None

        return self._optimization_result.to_dict()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(
        self,
    ) -> None:
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
            environment=self.scenario.initial_state.get("environment"),
        )

        self._agent_manager = AgentManager(
            self.world.state
        )

        # Calamity/infrastructure state must exist before the human-response
        # layer constructs its casualty infrastructure adapter.
        self._initialize_calamity()
        self._initialize_drainage()

        self._initialize_human_response()

        self._initialize_population_agents()

        self._initialize_risk()

        self._initialize_decision()

        self._optimization_result = None

        # Cache zone mapping in memory on initialization (LL-6)
        try:
            self._cached_zone_mapping = self._load_agent_zone_mapping()
        except Exception:
            pass

        self._build_pipeline()

        self._sync_world_time()

        self.world.state.record_event(
            {
                "type": (
                    "SIMULATION_INITIALIZED"
                ),
                "calamity": (
                    self.scenario
                    .calamity_type
                    .value
                ),
                "human_response_enabled": (
                    self._human_response_enabled
                ),
                "risk_engine_enabled": True,
                "decision_engine_enabled": True,
            }
        )

        self._initialized = True

        self._paused = False

    def _build_pipeline(self) -> None:
        """
        Construct the discrete simulation step pipeline.
        """
        self._pipeline = SimulationPipeline([
            RainfallStep(),
            DrainageStep(),
            SurfaceFloodStep(),
            FloodImpactStep(),
            InfrastructureCascadeStep(),
            HumanEvacuationStep(),
            RiskAssessmentStep(),
            DecisionInterventionStep(),
            MetricsStep(),
        ])

    def _create_step_context(self, delta_time: float) -> StepContext:
        """
        Create a StepContext snapshot reflecting current engine state.
        """
        return StepContext(
            clock=self.clock,
            world=self.world,
            scenario=self.scenario,
            delta_time=delta_time,
            flood=self._flood,
            flood_impact=self._flood_impact,
            infrastructure_network=self._infrastructure_network,
            panic_engine=self._panic_engine,
            evacuation_engine=self._evacuation_engine,
            crowd_engine=self._crowd_engine,
            casualties_engine=self._casualties_engine,
            risk_engine=self._risk_engine,
            intervention_rule_engine=self._algorithm_recommendation_engine,
            recommendation_engine=self._recommendation_engine,
            agent_manager=self._agent_manager,
            drainage_model=self._drainage_model,
            hyetograph=self._hyetograph,
            flood_zone_data=self._flood_zone_data,
            cached_zone_mapping=self._cached_zone_mapping,
            population_data=self._population_data,
            flood_water_levels=dict(
                self.world.state.environment.get("flood_water_levels", {})
            ),
            flood_impact_scores=dict(
                self.world.state.environment.get("flood_impact_scores", {})
            ),
            infrastructure_state=dict(self._infrastructure_state),
            panic_state=dict(self._panic_state),
            evacuation_routes=dict(self._evacuation_routes),
            crowd_state=dict(self._crowd_state),
            casualty_state=dict(self._casualty_state),
            casualty_population_reduction=dict(
                self._casualty_population_reduction
            ),
            risk_assessment=self._risk_assessment,
            risk_state=dict(self._risk_state),
            priority_state=dict(self._priority_state),
            recommendations=list(self._recommendations),
            active_interventions=list(self._active_interventions),
            human_response_enabled=self._human_response_enabled,
            panic_accumulator=self._panic_accumulator,
            population_model_step_seconds=self._population_model_step_seconds,
            panic_threshold=self._panic_threshold,
        )

    def _sync_from_step_context(self, context: StepContext) -> None:
        """
        Synchronize engine properties from the mutated StepContext.
        """
        self._infrastructure_state = context.infrastructure_state
        self._panic_state = context.panic_state
        self._evacuation_routes = context.evacuation_routes
        self._crowd_state = context.crowd_state
        self._casualty_state = context.casualty_state
        self._casualty_population_reduction = context.casualty_population_reduction
        self._risk_assessment = context.risk_assessment
        self._risk_state = context.risk_state
        self._priority_state = context.priority_state
        self._recommendations = context.recommendations
        self._panic_accumulator = context.panic_accumulator
        if context.drainage_state:
            self._drainage_state = dict(context.drainage_state)

    # ------------------------------------------------------------------
    # Human-response initialization
    # ------------------------------------------------------------------

    def _initialize_human_response(self) -> None:
        infra_data = self._build_casualty_infrastructure_data()
        res = PopulationInitializer.initialize_human_response(
            scenario=self.scenario,
            world=self.world,
            casualty_infrastructure_data=infra_data,
        )
        self._human_response_enabled = res["enabled"]
        self._panic_engine = res["panic_engine"]
        self._evacuation_engine = res["evacuation_engine"]
        self._crowd_engine = res["crowd_engine"]
        self._casualties_engine = res["casualties_engine"]
        self._panic_state = res["panic_state"]
        self._evacuation_routes = res["evacuation_routes"]
        self._crowd_state = res["crowd_state"]
        self._casualty_state = res["casualty_state"]
        self._population_data = res["population_data"]
        self._shelter_data = res["shelter_data"]

    def _initialize_population_agents(self) -> None:
        """Populate the authoritative WorldState with deterministic representative HumanAgent cohorts."""
        if self._agent_manager is None:
            raise RuntimeError("AgentManager must be initialized before population agents.")
        mapping = self._load_agent_zone_mapping()
        PopulationInitializer.populate_representative_agents(
            scenario=self.scenario,
            world=self.world,
            agent_manager=self._agent_manager,
            population_data=self._population_data,
            cached_zone_mapping=mapping,
            clock_tick=self.clock.current_tick,
        )

    def _load_agent_zone_mapping(self) -> dict[str, dict[str, Any]]:
        """Load and cache zone mapping using PopulationInitializer."""
        self._cached_zone_mapping = PopulationInitializer.load_zone_mapping(
            scenario=self.scenario,
            cached_zone_mapping=self._cached_zone_mapping,
            flood_zone_data=self._flood_zone_data,
        )
        return self._cached_zone_mapping

    # ------------------------------------------------------------------
    # Risk initialization
    # ------------------------------------------------------------------

    def _initialize_risk(self) -> None:
        pass

    def _initialize_decision(self) -> None:
        """Initialize the risk and decision layers via DecisionInitializer."""
        (
            self._risk_engine,
            self._algorithm_recommendation_engine,
            self._recommendation_engine,
        ) = DecisionInitializer.initialize_risk_and_decision(world=self.world)
        self._risk_assessment = None
        self._risk_state = {}
        self._priority_state = {}
        self._recommendations = []
        self._active_interventions = []

    def _build_casualty_infrastructure_data(self) -> dict[str, list[dict[str, Any]]]:
        """Produce normalized infrastructure node list for the casualty engine."""
        return DecisionInitializer.build_casualty_infrastructure_data(
            infrastructure_state=self._infrastructure_state,
            infrastructure_network=self._infrastructure_network,
        )

    # ------------------------------------------------------------------
    # Calamity
    # ------------------------------------------------------------------

    def _initialize_calamity(
        self,
    ) -> None:
        if self.scenario.calamity_type != CalamityType.FLOOD:
            raise ValueError(
                "Unsupported calamity type: "
                f"{self.scenario.calamity_type}"
            )

        (
            self._flood,
            self._hyetograph,
            self._flood_zone_data,
            self._flood_impact,
            self._infrastructure_network,
            self._drainage_model,
        ) = CalamityInitializer.initialize_flood_and_hydraulics(
            scenario=self.scenario,
            world=self.world,
        )
        self._infrastructure_state = {}

    def _initialize_drainage(self) -> None:
        # Drainage model is initialized within _initialize_calamity via CalamityInitializer
        pass

    # ------------------------------------------------------------------
    # Phase 14 — Intervention execution
    # ------------------------------------------------------------------

    def apply_intervention(
        self,
        intervention: Intervention | Mapping[
            str,
            Any,
        ],
    ) -> dict[str, Any]:
        """
        Explicitly execute an intervention against the current live
        Digital Twin.

        Phase 13 answers:

            "Which intervention performs best?"

        Phase 14 answers:

            "Apply this selected intervention to the current world."

        This method deliberately does NOT execute automatically after
        optimization. The caller must explicitly choose to intervene.

        The existing intervention algorithm remains authoritative for
        the mechanical effect. SimulationEngine only:

            1. validates the action,
            2. builds the algorithm input,
            3. executes the existing algorithm,
            4. transfers the resulting state into WorldState,
            5. records the intervention event.

        The current live simulation state is mutated only here.
        """

        if not self._initialized:
            self.initialize()

        normalized = (
            self._normalize_intervention(
                intervention
            )
        )

        intervention_id = (
            normalized["intervention_id"]
        )



        environment = (
            self._build_intervention_environment()
        )

        updated_environment = (
            self._algorithm_recommendation_engine
            .apply_intervention(
                intervention_id,
                environment,
            )
        )

        self._merge_intervention_environment(
            updated_environment
        )

        intervention_infra = self.world.state.environment.get("intervention_infrastructure", {})
        if intervention_infra:
            for node_id, node_state in intervention_infra.items():
                if node_id in self._infrastructure_state:
                    self._infrastructure_state[node_id].update(node_state)
                    self.world.state.environment["infrastructure"][node_id] = self._infrastructure_state[node_id]

        if self._risk_assessment:
            ctx = self._create_step_context(0.0)
            RiskAssessmentStep().execute(ctx)
            DecisionInterventionStep().execute(ctx)
            self._sync_from_step_context(ctx)

        self._active_interventions.append(dict(normalized))

        

        self._record_intervention_application()

        return dict(self._active_interventions[-1])

    def apply_selected_intervention(
        self,
    ) -> dict[str, Any]:
        """
        Apply the intervention selected by the most recent Phase 13
        optimization.

        Raises RuntimeError if optimization has not selected an action.
        """

        if self._optimization_result is None:
            raise RuntimeError(
                "No optimization result is available. "
                "Run optimize_interventions() first."
            )

        selected = (
            self._optimization_result
            .selected_intervention
        )

        if selected is None:
            raise RuntimeError(
                "Optimization did not select an intervention."
            )

        return self.apply_intervention(
            selected
        )


    @staticmethod
    def _normalize_intervention(
        intervention: Intervention | Mapping[
            str,
            Any,
        ],
    ) -> dict[str, Any]:
        """
        Normalize an Intervention dataclass or mapping into the single
        authoritative dictionary contract used by the live engine.
        """

        if isinstance(
            intervention,
            Intervention,
        ):
            normalized = intervention.to_dict()

        elif isinstance(
            intervention,
            Mapping,
        ):
            normalized = dict(
                intervention
            )

        else:
            raise TypeError(
                "intervention must be an Intervention or mapping."
            )

        intervention_id = (
            normalized.get(
                "intervention_id"
            )
            or normalized.get(
                "id"
            )
            or normalized.get(
                "action"
            )
        )

        if not intervention_id:
            raise ValueError(
                "Intervention must contain "
                "'intervention_id', 'id', or 'action'."
            )

        normalized[
            "intervention_id"
        ] = str(
            intervention_id
        )

        return normalized

    def _record_intervention_application(
        self,
    ) -> None:
        """
        Persist the current intervention state in the authoritative
        WorldState and emit a chronological event.
        """

        decision_state = (
            self.world.state.environment.get(
                "decision",
                {},
            )
        )

        if not isinstance(
            decision_state,
            Mapping,
        ):
            decision_state = {}

        self.world.state.environment[
            "decision"
        ] = {
            "priority": dict(
                self._priority_state
            ),
            "recommendations": [
                recommendation.to_dict()
                for recommendation
                in self._recommendations
            ],
            "active_interventions": [dict(i) for i in self._active_interventions],
        }

        self.world.state.environment[
            "intervention"
        ] = {
            "status": "ACTIVE",
            "applied": True,
            "applied_tick": (
                self.clock.current_tick
            ),
            "applied_simulation_time": (
                self.clock.simulation_time
            ),
            "actions": [dict(i) for i in self._active_interventions],
        }

        self.world.state.record_event(
            {
                "type": "INTERVENTION_APPLIED",
                "tick": (
                    self.clock.current_tick
                ),
                "simulation_time": (
                    self.clock.simulation_time
                ),
                "interventions": [dict(i) for i in self._active_interventions],
            }
        )


    # ------------------------------------------------------------------
    # Phase 13 — Baseline vs intervention optimization
    # ------------------------------------------------------------------

    def optimize_interventions(
        self,
        candidates: list[
            CandidateIntervention
        ],
    ) -> OptimizationResult:
        """
        Compare the current scenario with every applicable intervention.

        The baseline and every candidate are executed using independent
        SimulationEngine instances.

        The current engine/world is never reused as a mutable simulation
        container for a candidate run.

        This is the public Phase 13 entry point.
        """

        if not self._initialized:
            self.initialize()

        if not candidates:
            raise ValueError(
                "At least one intervention candidate is required."
            )

        baseline_scenario = {
            "scenario": self.scenario,
        }

        self._optimization_result = (
            self._optimization_engine.optimize(
                baseline_scenario=baseline_scenario,
                candidates=candidates,
            )
        )

        self.world.state.environment[
            "optimization"
        ] = self._optimization_result.to_dict()

        self.world.state.record_event(
            {
                "type": "OPTIMIZATION_COMPLETED",
                "tick": self.clock.current_tick,
                "candidate_count": len(
                    self._optimization_result.candidates
                ),
                "selected_intervention": (
                    self._optimization_result
                    .selected_intervention
                    .to_dict()
                    if (
                        self._optimization_result
                        .selected_intervention
                        is not None
                    )
                    else None
                ),
            }
        )

        return self._optimization_result

    def _provide_simulation_evaluation(
        self,
        scenario_payload: Mapping[
            str,
            Any,
        ] | None,
    ) -> SimulationEvaluation:
        """
        Execute one isolated scenario and return its SimulationEvaluation via SimulationEvaluator.
        """
        return SimulationEvaluator.provide_simulation_evaluation(
            engine_cls=SimulationEngine,
            scenario_payload=scenario_payload,
            base_scenario=self.scenario,
            initial_entities=self._initial_entities,
            cached_zone_mapping=self._cached_zone_mapping,
        )

    def _build_simulation_evaluation(
        self,
    ) -> SimulationEvaluation:
        """Derive SimulationEvaluation from self via SimulationEvaluator."""
        return SimulationEvaluator.build_simulation_evaluation(self)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def pause(
        self,
    ) -> None:

        self._paused = True

    def resume(
        self,
    ) -> None:

        if not self._initialized:
            raise RuntimeError(
                "Simulation must be initialized "
                "before resuming."
            )

        self._paused = False

    def reset(
        self,
    ) -> None:

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

        self._casualty_population_reduction = {}

        self._population_data = None

        self._shelter_data = None

        self._risk_engine = RiskEngine()

        self._risk_assessment = None

        self._risk_state = {}

        self._algorithm_recommendation_engine = (
            AlgorithmRecommendationEngine()
        )

        self._recommendation_engine = (
            RecommendationEngine()
        )

        self._priority_state = {}

        self._recommendations = []

        self._active_interventions = []

        self._cached_zone_mapping = None

        self._pipeline = None

        self._optimization_result = None

        self._human_response_enabled = False

        self._panic_accumulator = 0.0

        self._initialized = False

        self._paused = False

    # ------------------------------------------------------------------
    # Simulation progression
    # ------------------------------------------------------------------

    def step(
        self,
    ) -> float:
        """
        Advance the simulation by one tick using the pipeline.

        Execution order:
            1. RainfallStep
            2. DrainageStep
            3. SurfaceFloodStep
            4. FloodImpactStep
            5. InfrastructureCascadeStep
            6. HumanEvacuationStep
            7. RiskAssessmentStep
            8. DecisionInterventionStep
            9. MetricsStep
        """

        if not self._initialized:
            raise RuntimeError(
                "SimulationEngine must be initialized before stepping."
            )

        if self._paused:
            raise RuntimeError(
                "Simulation is paused."
            )

        if self.is_complete:
            raise RuntimeError(
                "Simulation duration has already "
                "been reached."
            )

        delta_time = self.clock.advance()

        self._sync_world_time()

        # Build context, execute all pipeline steps, sync state back
        context = self._create_step_context(delta_time)
        self._pipeline.execute(context)
        self._sync_from_step_context(context)

        # Handle pending scenario intervention flagged by DecisionStep
        pending = self.world.state.environment.pop(
            "_pending_scenario_intervention", None
        )
        if pending is not None:
            self._apply_scenario_intervention(pending)

        return delta_time

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
    # Intervention application
    # ------------------------------------------------------------------

    def _apply_scenario_intervention(
        self,
        intervention: Mapping[str, Any],
    ) -> None:
        """Apply an explicitly supplied Scenario intervention using the authoritative pipeline."""
        if not isinstance(intervention, Mapping):
            raise TypeError("Scenario.intervention must be a mapping.")
        self.apply_intervention(intervention)

    def _build_intervention_environment(self) -> dict[str, Any]:
        """Build the environment contract expected by the existing intervention algorithm."""
        zones = {}
        flood_zones = self.world.state.environment.get("flood_water_levels", {})
        if isinstance(flood_zones, Mapping):
            for zone_id, water_level in flood_zones.items():
                drainage_rate = 0.0
                if self._flood is not None and self._flood.propagator is not None:
                    zone_state = self._flood.propagator.state.get(zone_id, {})
                    if isinstance(zone_state, Mapping):
                        drainage_rate = float(zone_state.get("drainage_capacity", 0.0))
                zones[str(zone_id)] = {
                    "water_level": float(water_level),
                    "drainage_rate": max(0.0, drainage_rate),
                }

        transit_capacities = {}
        if self._crowd_engine is not None:
            transit_capacities = {
                str(zone_id): float(capacity)
                for zone_id, capacity in self._crowd_engine.transit_capacities.items()
            }

        infrastructure_nodes = {}
        for node_id, node_state in self._infrastructure_state.items():
            infrastructure_nodes[str(node_id)] = {
                "capacity": float(node_state.get("capacity", 1.0)),
                "backup_power": float(
                    self._infrastructure_network.nodes.get(node_id, {}).get("backup_power", 0.0)
                    if self._infrastructure_network else 0.0
                ),
                "zone_id": node_state.get("zone_id"),
                "type": node_state.get("type", "UNKNOWN"),
            }

        return {
            "zones": zones,
            "transit_capacities": transit_capacities,
            "infrastructure_nodes": infrastructure_nodes,
        }

    def _merge_intervention_environment(
        self,
        intervention_environment: Mapping[str, Any],
    ) -> None:
        """Merge intervention effects back into WorldState environment."""
        zones = intervention_environment.get("zones", {})
        if isinstance(zones, Mapping):
            if "intervention_zones" not in self.world.state.environment:
                self.world.state.environment["intervention_zones"] = {}
            self.world.state.environment["intervention_zones"].update({
                str(zid): dict(zstate) if isinstance(zstate, Mapping) else zstate
                for zid, zstate in zones.items()
            })

        transit_capacities = intervention_environment.get("transit_capacities", {})
        if isinstance(transit_capacities, Mapping):
            if "transit_capacities" not in self.world.state.environment:
                self.world.state.environment["transit_capacities"] = {}
            self.world.state.environment["transit_capacities"].update({
                str(zid): float(cap) for zid, cap in transit_capacities.items()
            })

        infrastructure_nodes = intervention_environment.get("infrastructure_nodes", {})
        if isinstance(infrastructure_nodes, Mapping):
            if "intervention_infrastructure" not in self.world.state.environment:
                self.world.state.environment["intervention_infrastructure"] = {}
            self.world.state.environment["intervention_infrastructure"].update({
                str(nid): dict(nstate) if isinstance(nstate, Mapping) else nstate
                for nid, nstate in infrastructure_nodes.items()
            })


