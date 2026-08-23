import joblib
import pandas as pd
import numpy as np
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.features import FLOOD_FEATURE_COLUMNS, normalize_flood_feature_dict, normalize_flood_feature_frame

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
        # Validate and enforce the canonical flood schema
        df = normalize_flood_feature_frame(pd.DataFrame([normalize_flood_feature_dict(features_dict)]))
        
        # Predict and clamp between 0.0 and 1.0
        prediction = self.model.predict(df)[0]
        return float(np.clip(prediction, 0.0, 1.0))
        
    def batch_predict(self, zones_feature_list):
        """
        Takes a list of dictionaries for simulation efficiency (predicting all zones at once).
        """
        normalized_rows = [normalize_flood_feature_dict(row) for row in zones_feature_list]
        df = normalize_flood_feature_frame(pd.DataFrame(normalized_rows))
        predictions = self.model.predict(df)
        return np.clip(predictions, 0.0, 1.0).tolist()

if __name__ == "__main__":
    # Standalone test logic
    predictor = FloodImpactPredictor()
    
    # Mocking a severe flood in a dense area with low intervention
    test_zone = {
        'elevation': 0.2,
        'flood_exposure': 0.85,
        'severity': 3,
        'day': 5,
        'intervention': 0.10,
        'drainage_weakness': 0.75,
        'infra_vuln': 0.60,
    }
    
    score = predictor.predict_impact(test_zone)
    print(f"Test Predicted Impact Score: {score:.3f}")