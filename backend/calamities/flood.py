from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from algorithms.flood.propagation import FloodPropagator
from core.enums import CalamityType

from calamities.base import Calamity


class Flood(Calamity):
    """
    SATARK flood calamity.

    This class orchestrates the existing FloodPropagator algorithm.

    The underlying propagator advances in discrete flood-model steps.
    This wrapper controls when those steps occur relative to the
    simulation clock.

    Flood impact ML prediction is intentionally handled elsewhere.
    """

    calamity_type = CalamityType.FLOOD

    def __init__(
        self,
        zone_mapping_path: str | Path,
        rainfall_intensity: float = 0.0,
        *,
        model_step_seconds: float = 1.0,
        parameters: Dict[str, Any] | None = None,
    ) -> None:

        super().__init__(
            parameters
        )

        if rainfall_intensity < 0:
            raise ValueError(
                "Rainfall intensity cannot be negative."
            )

        if model_step_seconds <= 0:
            raise ValueError(
                "model_step_seconds must be greater than 0."
            )

        self.zone_mapping_path = str(
            zone_mapping_path
        )

        self.rainfall_intensity = (
            rainfall_intensity
        )

        self.model_step_seconds = (
            float(model_step_seconds)
        )

        self._elapsed_seconds = 0.0

        self.propagator: FloodPropagator | None = None

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Initialize the existing FloodPropagator.
        """

        self.propagator = FloodPropagator(
            self.zone_mapping_path
        )

        self._elapsed_seconds = 0.0

        self._state = {
            "calamity_type": (
                self.calamity_type.value
            ),
            "rainfall_intensity": (
                self.rainfall_intensity
            ),
            "water_levels": {
                zone_id: 0.0
                for zone_id in (
                    self.propagator.state
                )
            },
        }

        self._initialized = True

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def step(
        self,
        delta_time: float,
    ) -> Dict[str, Any]:
        """
        Advance the flood simulation according to elapsed simulation time.

        The underlying FloodPropagator performs one discrete flood-model
        step at a time. This wrapper prevents one flood-model hour from
        being executed on every 10 Hz simulation tick.

        Returns the latest flood state.
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

        self._elapsed_seconds += float(
            delta_time
        )

        steps = int(
            self._elapsed_seconds
            // self.model_step_seconds
        )

        if steps <= 0:
            return self.state

        self._elapsed_seconds -= (
            steps
            * self.model_step_seconds
        )

        for _ in range(steps):
            new_state = (
                self.propagator.simulate_hour(
                    self.rainfall_intensity
                )
            )

            water_levels = {
                zone_id: float(
                    water_level
                )
                for zone_id, water_level
                in new_state.items()
            }

            self._state = {
                "calamity_type": (
                    self.calamity_type.value
                ),
                "rainfall_intensity": (
                    self.rainfall_intensity
                ),
                "water_levels": water_levels,
            }

        return self.state

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

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

        self.rainfall_intensity = (
            rainfall_intensity
        )

        if self._initialized:
            self._state[
                "rainfall_intensity"
            ] = rainfall_intensity

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """
        Reset flood state and timing accumulator.
        """

        super().reset()

        self.propagator = None

        self._elapsed_seconds = 0.0