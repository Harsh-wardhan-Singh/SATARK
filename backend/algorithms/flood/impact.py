"""
Flood impact calculation adapter.

This module converts live flood state + zone metadata into the
canonical ML feature schema and delegates prediction to ml.predict.

It does not load the ML model directly.
"""

from __future__ import annotations

from typing import Any, Mapping

from ml.features import zone_to_flood_features
from ml.predict import FloodImpactPredictor


class FloodImpactEngine:
    """
    Adapter between the flood simulation and the flood ML model.

    Responsibilities:
        - receive current flood state
        - receive zone metadata
        - construct canonical ML features
        - delegate prediction to FloodImpactPredictor
        - return zone -> impact score

    It does not:
        - load joblib directly
        - call sklearn directly
        - simulate water
        - modify infrastructure
        - modify agents
        - calculate risk
    """

    def __init__(
        self,
        predictor: FloodImpactPredictor | None = None,
    ) -> None:

        self.predictor = (
            predictor
            if predictor is not None
            else FloodImpactPredictor()
        )

    def calculate_impacts(
        self,
        flood_states: Mapping[str, float],
        zones_data: Mapping[
            str,
            Mapping[str, Any]
        ],
        severity: int,
        day: int,
        intervention: float,
    ) -> dict[str, float]:
        """
        Calculate the flood impact score for every zone.

        Args:
            flood_states:
                Mapping of zone ID -> current water level.

            zones_data:
                Mapping of zone ID -> zone metadata.

            severity:
                Flood severity level expected by the ML model.
                Must be 1, 2, or 3.

            day:
                Simulation/disaster day expected by the ML model.
                Must be within 1..7.

            intervention:
                Intervention level expected by the ML model.
                Must be within 0..1.

        Returns:
            Mapping of zone ID -> impact score in [0, 1].
        """

        zone_features = []

        zone_ids = []

        for zone_id, water_level in (
            flood_states.items()
        ):
            zone = zones_data.get(
                zone_id,
                {},
            )

            features = zone_to_flood_features(
                zone_id=zone_id,
                zone_data=zone,
                water_level=float(
                    water_level
                ),
                severity=severity,
                day=day,
                intervention=intervention,
            )

            zone_ids.append(
                zone_id
            )

            zone_features.append(
                features
            )

        predictions = (
            self.predictor.batch_predict(
                zone_features
            )
        )

        return {
            zone_id: prediction
            for zone_id, prediction in zip(
                zone_ids,
                predictions,
            )
        }