from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from core.types import SimulationConfig


@dataclass(frozen=True)
class Scenario:
    """
    Immutable description of one simulation scenario.

    Scenario describes what should be simulated.
    WorldState contains what is currently happening.
    """

    config: SimulationConfig

    initial_state: Mapping[str, Any] = field(
        default_factory=dict
    )

    parameters: Mapping[str, Any] = field(
        default_factory=dict
    )

    intervention: Mapping[str, Any] | None = None

    @property
    def duration(self) -> float:
        return self.config.duration

    @property
    def tick_rate(self) -> float:
        return self.config.tick_rate

    @property
    def calamity_type(self):
        return self.config.calamity_type

    @property
    def random_seed(self) -> int | None:
        return self.config.random_seed

    def get_parameter(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        return self.parameters.get(
            key,
            default,
        )

    def get_initial_state(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        return self.initial_state.get(
            key,
            default,
        )