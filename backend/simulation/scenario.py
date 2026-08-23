from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from core.types import SimulationConfig


@dataclass(frozen=True)
class Scenario:
    """
    Immutable description of one SATARK simulation.

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

    # ------------------------------------------------------------------
    # Core configuration
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Generic access
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Flood parameters
    # ------------------------------------------------------------------

    @property
    def rainfall_intensity(self) -> float:
        """
        Rainfall intensity supplied to FloodPropagator.
        """

        value = float(
            self.get_parameter(
                "rainfall_intensity",
                0.0,
            )
        )

        if value < 0:
            raise ValueError(
                "rainfall_intensity cannot be negative."
            )

        return value

    @property
    def severity(self) -> int:
        """
        Flood ML severity.

        The current training contract uses:
            1, 2, 3
        """

        value = int(
            self.get_parameter(
                "severity",
                1,
            )
        )

        if value not in (1, 2, 3):
            raise ValueError(
                "severity must be 1, 2, or 3."
            )

        return value

    @property
    def intervention_level(self) -> float:
        """
        Flood intervention level in [0, 1].
        """

        value = float(
            self.get_parameter(
                "intervention",
                0.0,
            )
        )

        if not 0.0 <= value <= 1.0:
            raise ValueError(
                "intervention must be between 0.0 and 1.0."
            )

        return value

    @property
    def zone_mapping_path(self) -> str | None:
        """
        Path to glb_zone_mapping.json.
        """

        value = self.get_parameter(
            "zone_mapping_path",
            None,
        )

        if value is None:
            return None

        return str(value)

    @property
    def infrastructure_path(self) -> str | None:
        """
        Path to infrastructure.json.
        """

        value = self.get_parameter(
            "infrastructure_path",
            None,
        )

        if value is None:
            return None

        return str(value)

    @property
    def flood_model_step_seconds(self) -> float:
        """
        Simulation seconds represented by one FloodPropagator step.

        This is deliberately configurable because the underlying flood
        algorithm is hour-based while SATARK's simulation clock is a
        configurable accelerated clock.
        """

        value = float(
            self.get_parameter(
                "flood_model_step_seconds",
                1.0,
            )
        )

        if value <= 0:
            raise ValueError(
                "flood_model_step_seconds must be greater than 0."
            )

        return value