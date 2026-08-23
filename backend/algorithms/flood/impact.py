import joblib
import os
import numpy as np
import pandas as pd
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.features import build_flood_feature_row, normalize_flood_feature_frame

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

    def calculate_impacts(self, flood_states, zones_data, severity, day, intervention_level):
        """
        Takes current water levels from FloodPropagator and zone metadata,
        and uses the ML model to predict the impact score (0.0 to 1.0) for each zone.
        """
        impact_results = {}
        
        for zone_id, water_level in flood_states.items():
            zone = zones_data.get(zone_id, {})

            # Build the canonical training schema in the exact same order.
            features = build_flood_feature_row(
                elevation=zone.get('elevation', zone.get('center_normalized', {}).get('y', 0.5)),
                flood_exposure=min(1.0, max(0.0, water_level / 2.0)),
                severity=severity,
                day=day,
                intervention=intervention_level,
                drainage_weakness=1.0 - zone.get('drainage_capacity', zone.get('drainage_rate', 0.5)),
                infra_vuln=zone.get('infra_vuln', zone.get('infrastructure_vulnerability', 0.5)),
            )
            features = normalize_flood_feature_frame(pd.DataFrame([features]))
            
            # Predict impact using the ML model
            predicted_impact = self.model.predict(features)[0]
            impact_results[zone_id] = float(np.clip(predicted_impact, 0.0, 1.0))
            
        return impact_results