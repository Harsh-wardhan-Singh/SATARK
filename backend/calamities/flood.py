from pathlib import Path
from typing import Any, Dict

from core.enums import CalamityType

from calamities.base import Calamity
from algorithms.flood.propagation import FloodPropagator


class Flood(Calamity):
    """
    SATARK flood calamity.

    This class orchestrates the existing FloodPropagator algorithm.

    Responsibilities:
        - configure flood parameters
        - initialize flood propagation
        - advance flood propagation
        - expose zone-level water levels

    Flood impact ML prediction is intentionally handled elsewhere.
    """

    calamity_type = CalamityType.FLOOD

    def __init__(
        self,
        zone_mapping_path: str | Path,
        rainfall_intensity: float = 0.0,
        parameters: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(parameters)

        if rainfall_intensity < 0:
            raise ValueError(
                "Rainfall intensity cannot be negative."
            )

        self.zone_mapping_path = str(
            zone_mapping_path
        )

        self.rainfall_intensity = rainfall_intensity

        self.propagator: FloodPropagator | None = None

    def initialize(self) -> None:
        """
        Initialize the existing flood propagation engine.
        """
        self.propagator = FloodPropagator(
            self.zone_mapping_path
        )

        self._state = {
            "calamity_type": self.calamity_type.value,
            "rainfall_intensity": self.rainfall_intensity,
            "water_levels": {
                zone_id: 0.0
                for zone_id in self.propagator.state
            },
        }

        self._initialized = True

    def step(
        self,
        delta_time: float,
    ) -> Dict[str, Any]:
        """
        Advance the flood simulation by one flood-model step.

        The existing FloodPropagator exposes a `simulate_hour`
        operation. We therefore preserve its current timestep
        semantics rather than rewriting the underlying algorithm.
        """
        self._require_initialized()

        if delta_time < 0:
            raise ValueError(
                "delta_time cannot be negative."
            )

        if self.propagator is None:
            raise RuntimeError(
                "Flood propagator is unavailable."
            )

        new_state = self.propagator.simulate_hour(
            self.rainfall_intensity
        )

        water_levels = {
            zone_id: float(data["water_level"])
            for zone_id, data in new_state.items()
        }

        self._state = {
            "calamity_type": self.calamity_type.value,
            "rainfall_intensity": self.rainfall_intensity,
            "water_levels": water_levels,
        }

        return self.state

    def set_rainfall(
        self,
        rainfall_intensity: float,
    ) -> None:
        """
        Change rainfall intensity for future flood steps.
        """
        if rainfall_intensity < 0:
            raise ValueError(
                "Rainfall intensity cannot be negative."
            )

        self.rainfall_intensity = rainfall_intensity

        if self._initialized:
            self._state["rainfall_intensity"] = (
                rainfall_intensity
            )

    def reset(self) -> None:
        """
        Reset flood state.
        """
        super().reset()

        self.propagator = None
