from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from ml.features import FLOOD_FEATURE_COLUMNS
from ml.predict import FloodImpactPredictor


class FloodImpactEngine:
    """
    Adapter between the flood simulation and the flood ML model.

    Responsibilities:
        - receive current flood state
        - receive zone metadata and optional drainage state
        - construct canonical ML feature matrix via fast NumPy vectorization
        - delegate prediction to FloodImpactPredictor
        - return zone -> impact score

    It does not:
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
        zones_data: Mapping[str, Mapping[str, Any]],
        *,
        severity: int,
        day: int,
        intervention_level: float,
        drainage_state: Mapping[str, Any] | None = None,
    ) -> dict[str, float]:
        """
        Calculate one ML impact score per zone using a pure NumPy feature pipeline.

        Constructs a contiguous C-array directly in FLOOD_FEATURE_COLUMNS order,
        eliminating intermediate pandas DataFrame and dictionary roundtrips.
        """
        if not 1 <= int(severity) <= 3:
            raise ValueError(
                "severity must be between 1 and 3."
            )

        if not 0.0 <= float(intervention_level) <= 1.0:
            raise ValueError(
                "intervention_level must be between 0.0 and 1.0."
            )

        n_zones = len(flood_states)
        if n_zones == 0:
            return {}

        zone_drainage = (
            drainage_state.get("zone_drainage", {})
            if drainage_state
            else {}
        )

        n_features = len(FLOOD_FEATURE_COLUMNS)
        X = np.empty((n_zones, n_features), dtype=np.float64)
        zone_ids: list[str] = []

        for i, (zone_id, water_level) in enumerate(flood_states.items()):
            zone = zones_data.get(zone_id, {})

            elevation = zone.get("elevation")
            if elevation is None:
                elevation = (
                    zone.get("center_normalized", {}).get("y", 0.5)
                )

            drainage_capacity = float(
                zone.get(
                    "drainage_capacity",
                    zone.get("drainage_rate", 0.5),
                )
            )

            infra_vuln = float(
                zone.get(
                    "infra_vuln",
                    zone.get("infrastructure_vulnerability", 0.5),
                )
            )

            # Compute pipe surcharge from drainage coupling if present
            pipe_surcharge = 0.0
            if zone_drainage:
                zd = zone_drainage.get(zone_id, {})
                surcharge_rate = float(zd.get("surcharge_rate", 0.0))
                if surcharge_rate > 0.0:
                    pipe_surcharge = min(1.0, surcharge_rate / 2.0)
                elif zd.get("is_surcharging", False) or float(zd.get("pipe_utilization", 0.0)) > 1.0:
                    pipe_surcharge = 0.5

            flood_exposure = min(1.0, max(0.0, float(water_level) / 2.0))
            drainage_weakness = min(1.0, max(0.0, 1.0 - drainage_capacity))

            X[i, 0] = float(elevation)
            X[i, 1] = flood_exposure
            X[i, 2] = float(severity)
            X[i, 3] = float(day)
            X[i, 4] = float(intervention_level)
            X[i, 5] = min(1.0, max(0.0, drainage_capacity))
            X[i, 6] = drainage_weakness
            X[i, 7] = min(1.0, max(0.0, infra_vuln))
            X[i, 8] = min(1.0, max(0.0, pipe_surcharge))

            zone_ids.append(zone_id)

        predictions = self.predictor.predict_features_matrix(X)

        return {
            zone_id: float(prediction)
            for zone_id, prediction in zip(zone_ids, predictions)
        }