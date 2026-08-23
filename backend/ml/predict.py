import joblib
import pandas as pd
import numpy as np
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
MODEL_PATH = os.path.join(PROJECT_ROOT, 'ml', 'flood_impact_model.joblib')

class FloodImpactPredictor:
    def __init__(self, model_path=MODEL_PATH):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at {model_path}. Run ml/train.py first.")
        self.model = joblib.load(model_path)
        
    def predict_impact(self, features_dict):
        """
        Takes a single dictionary of zone features and returns the predicted impact score.
        """
        # XGBoost/RandomForest expect consistent feature names, so we use a DataFrame
        df = pd.DataFrame([features_dict])
        
        # Predict and clamp between 0.0 and 1.0
        prediction = self.model.predict(df)[0]
        return float(np.clip(prediction, 0.0, 1.0))
        
    def batch_predict(self, zones_feature_list):
        """
        Takes a list of dictionaries for simulation efficiency (predicting all zones at once).
        """
        df = pd.DataFrame(zones_feature_list)
        predictions = self.model.predict(df)
        return np.clip(predictions, 0.0, 1.0).tolist()

if __name__ == "__main__":
    # Standalone test logic
    predictor = FloodImpactPredictor()
    
    # Mocking a severe flood in a dense area with low intervention
    test_zone = {
        'flood_exposure': 0.85,
        'population_density': 0.90,
        'drainage_weakness': 0.75,
        'infra_vulnerability': 0.60,
        'rainfall_severity': 0.80,
        'duration_factor': 1.20,
        'intervention_level': 0.10
    }
    
    score = predictor.predict_impact(test_zone)
    print(f"Test Predicted Impact Score: {score:.3f}")