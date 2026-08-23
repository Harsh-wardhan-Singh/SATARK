from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Tuple

from core.types import SimulationConfig
from twin.entity import Entity


@dataclass
class Scenario:
    """
    Immutable-style description of a simulation setup.

    Scenario describes the conditions with which a simulation begins.
    It is not the live simulation state.

    The live state belongs to the Digital Twin / WorldState.
    """

    config: SimulationConfig

    initial_entities: Tuple[Entity, ...] = field(default_factory=tuple)

    initial_environment: Dict[str, float] = field(
        default_factory=dict
    )

    parameters: Dict[str, Any] = field(
        default_factory=dict
    )

    intervention: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """
        Normalize scenario inputs and validate basic configuration.
        """
        self.initial_entities = tuple(self.initial_entities)

        self.initial_environment = dict(
            self.initial_environment
        )

        self.parameters = dict(self.parameters)

        if self.intervention is not None:
            self.intervention = dict(self.intervention)

    @property
    def duration(self) -> float:
        """
        Return the configured simulation duration.
        """
        return self.config.duration

    @property
    def tick_rate(self) -> float:
        """
        Return the configured simulation tick rate.
        """
        return self.config.tick_rate

    @property
    def random_seed(self) -> Optional[int]:
        """
        Return the configured random seed.
        """
        return self.config.random_seed

    @property
    def calamity_type(self):
        """
        Return the configured calamity type.
        """
        return self.config.calamity_type

    def get_initial_entities(self) -> Tuple[Entity, ...]:
        """
        Return the entities that should exist when the simulation starts.
        """
        return self.initial_entities

    def get_initial_environment(self) -> Dict[str, float]:
        """
        Return a copy of the initial environment configuration.
        """
        return dict(self.initial_environment)

    def get_parameters(self) -> Dict[str, Any]:
        """
        Return a copy of scenario-specific parameters.
        """
        return dict(self.parameters)