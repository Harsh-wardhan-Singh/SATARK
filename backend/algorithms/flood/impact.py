from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from ml.features import (
    build_flood_feature_row,
    normalize_flood_feature_frame,
)
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
    ) -> dict[str, float]:
        """
        Calculate one ML impact score per zone.

        The feature order is controlled by ml.features so the runtime
        schema remains identical to the training schema.
        """

        if not 1 <= int(severity) <= 3:
            raise ValueError(
                "severity must be between 1 and 3."
            )

        if not 0.0 <= float(intervention_level) <= 1.0:
            raise ValueError(
                "intervention_level must be between 0.0 and 1.0."
            )

        feature_rows: list[dict[str, Any]] = []
        zone_ids: list[str] = []

        for zone_id, water_level in flood_states.items():

            zone = zones_data.get(
                zone_id,
                {},
            )

            elevation = zone.get(
                "elevation"
            )

            if elevation is None:
                elevation = (
                    zone
                    .get(
                        "center_normalized",
                        {},
                    )
                    .get(
                        "y",
                        0.5,
                    )
                )

            drainage_capacity = float(
                zone.get(
                    "drainage_capacity",
                    zone.get(
                        "drainage_rate",
                        0.5,
                    ),
                )
            )

            infra_vuln = float(
                zone.get(
                    "infra_vuln",
                    zone.get(
                        "infrastructure_vulnerability",
                        0.5,
                    ),
                )
            )

            feature_rows.append(
                build_flood_feature_row(
                    elevation=float(
                        elevation
                    ),
                    flood_exposure=min(
                        1.0,
                        max(
                            0.0,
                            float(water_level) / 2.0,
                        ),
                    ),
                    severity=int(
                        severity
                    ),
                    day=int(
                        day
                    ),
                    intervention=float(
                        intervention_level
                    ),
                    drainage_weakness=min(
                        1.0,
                        max(
                            0.0,
                            1.0 - drainage_capacity,
                        ),
                    ),
                    infra_vuln=min(
                        1.0,
                        max(
                            0.0,
                            infra_vuln,
                        ),
                    ),
                )
            )

            zone_ids.append(
                zone_id
            )

        if not feature_rows:
            return {}

        feature_frame = (
            normalize_flood_feature_frame(
                pd.DataFrame(
                    feature_rows
                )
            )
        )

        predictions = (
            self.predictor.batch_predict(
                feature_frame.to_dict(
                    orient="records"
                )
            )
        )

        return {
            zone_id: float(prediction)
            for zone_id, prediction in zip(
                zone_ids,
                predictions,
            )
        }