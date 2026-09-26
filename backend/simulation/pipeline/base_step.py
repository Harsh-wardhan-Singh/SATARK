from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping

from simulation.clock import SimulationClock
from simulation.scenario import Scenario
from simulation.world import SimulationWorld

logger = logging.getLogger(__name__)


@dataclass
class StepContext:
    """
    Mutable context passed through each simulation step in the pipeline.

    Holds references to all simulation engines, clocks, Digital Twin state,
    and intra-tick calculated states. The pipeline mutates this sequentially.
    """

    clock: SimulationClock
    world: SimulationWorld
    scenario: Scenario
    delta_time: float = 0.0

    # Engine references
    flood: Any | None = None
    flood_impact: Any | None = None
    infrastructure_network: Any | None = None
    panic_engine: Any | None = None
    evacuation_engine: Any | None = None
    crowd_engine: Any | None = None
    casualties_engine: Any | None = None
    risk_engine: Any | None = None
    intervention_rule_engine: Any | None = None
    recommendation_engine: Any | None = None
    agent_manager: Any | None = None
    drainage_model: Any | None = None
    hyetograph: Any | None = None

    # Flood domain data
    flood_zone_data: dict[str, dict[str, Any]] = field(default_factory=dict)
    cached_zone_mapping: dict[str, dict[str, Any]] | None = None
    population_data: Mapping[str, Any] | None = None

    # Intra-tick states
    flood_water_levels: dict[str, float] = field(default_factory=dict)
    flood_impact_scores: dict[str, float] = field(default_factory=dict)
    infrastructure_state: dict[str, dict[str, Any]] = field(default_factory=dict)
    panic_state: dict[str, float] = field(default_factory=dict)
    evacuation_routes: dict[str, Any] = field(default_factory=dict)
    crowd_state: dict[str, Any] = field(default_factory=dict)
    casualty_state: dict[str, Any] = field(default_factory=dict)
    casualty_population_reduction: dict[str, float] = field(default_factory=dict)
    drainage_state: dict[str, Any] = field(default_factory=dict)

    # Risk and Decision states
    risk_assessment: Any | None = None
    risk_state: dict[str, Any] = field(default_factory=dict)
    priority_state: dict[str, Any] = field(default_factory=dict)
    recommendations: list[Any] = field(default_factory=list)
    active_interventions: list[dict[str, Any]] = field(default_factory=list)

    # Human response timing flags
    human_response_enabled: bool = False
    panic_accumulator: float = 0.0
    population_model_step_seconds: float = 1.0
    panic_threshold: float = 0.5


class SimulationStep(ABC):
    """
    Base class for a discrete simulation step in the SATARK pipeline.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the simulation step."""
        ...

    @abstractmethod
    def execute(self, context: StepContext) -> None:
        """
        Execute this step using the provided StepContext.
        """
        ...


class SimulationPipeline:
    """
    Orchestrates the sequential execution of registered SimulationSteps.
    """

    def __init__(self, steps: list[SimulationStep] | None = None) -> None:
        self.steps: list[SimulationStep] = steps if steps is not None else []

    def add_step(self, step: SimulationStep) -> None:
        self.steps.append(step)

    def execute(self, context: StepContext) -> None:
        for step in self.steps:
            logger.debug("Executing simulation step: %s", step.name)
            step.execute(context)
