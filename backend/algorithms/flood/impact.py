import joblib
import os
import numpy as np

class FloodImpactEngine:
    def __init__(self, model_path="ml/flood_impact_model.joblib"):
        # Load the pre-trained Random Forest model
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Trained ML model not found at {model_path}. Run ml/train.py first.")
        self.model = joblib.load(model_path)

    def calculate_impacts(self, flood_states, zones_data, duration_factor, intervention_level):
        """
        Takes current water levels from FloodPropagator and zone metadata,
        and uses the ML model to predict the impact score (0.0 to 1.0) for each zone.
        """
        impact_results = {}
        
        for zone_id, water_level in flood_states.items():
            zone = zones_data.get(zone_id, {})
            
            # Extract features expected by the ML model
            # ['flood_exposure', 'population_density', 'drainage_weakness', 'infra_vulnerability', 'rainfall_severity', 'duration_factor', 'intervention_level']
            
            # Normalize water level to act as flood exposure proxy if needed
            flood_exposure = min(1.0, water_level / 2.0) # Scale factor depending on max water height
            population_density = zone.get('population_density', 0.5)
            drainage_weakness = 1.0 - zone.get('drainage_capacity', 0.5)
            infra_vulnerability = zone.get('infrastructure_vulnerability', 0.5)
            rainfall_severity = zone.get('current_rainfall', 0.5)
            
            # Construct feature vector for this zone
            features = np.array([[
                flood_exposure,
                population_density,
                drainage_weakness,
                infra_vulnerability,
                rainfall_severity,
                duration_factor,
                intervention_level
            ]])
            
            # Predict impact using the ML model
            predicted_impact = self.model.predict(features)[0]
            impact_results[zone_id] = float(np.clip(predicted_impact, 0.0, 1.0))
            
        return impact_results