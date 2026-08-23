import pandas as pd
import os
import joblib
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

def evaluate():
    model_path = os.path.join(SCRIPT_DIR, 'flood_impact_model.joblib')
    data_path = os.path.join(PROJECT_ROOT, 'data', 'raw', 'flood_model_training.csv')
    
    model = joblib.load(model_path)
    df = pd.read_csv(data_path)
    
    feature_cols = ['elevation', 'flood_exposure', 'severity', 'day', 'intervention', 'drainage_weakness', 'infra_vuln']
    X = df[feature_cols]
    y_true = df['impact_score']
    
    y_pred = model.predict(X)
    
    print("\n--- OVERALL METRICS ---")
    print(f"MSE: {mean_squared_error(y_true, y_pred):.5f}")
    print(f"MAE: {mean_absolute_error(y_true, y_pred):.5f}")
    print(f"R2 Score: {r2_score(y_true, y_pred):.4f}")
    print(f"Prediction Span: Min={y_pred.min():.4f}, Max={y_pred.max():.4f}\n")

    print("--- EDGE CASE SIMULATIONS ---")
    edge_cases = [
        {
            "name": "1. Doomsday (Lowest elev, Max severity, Day 7, NO intervention, High vulnerability)",
            "features": [0.0, 1.0, 3, 7, 0.0, 1.0, 1.0]
        },
        {
            "name": "2. Absolute Safety (Highest elev, Min severity, Day 1, MAX intervention, Perfect drainage)",
            "features": [1.0, 0.0, 1, 1, 1.0, 0.0, 0.0]
        },
        {
            "name": "3. Rescue Mitigation (Low elev, Max severity, Day 4, MAX intervention, Med vulnerability)",
            "features": [0.2, 0.8, 3, 4, 1.0, 0.5, 0.5]
        }
    ]
    
    for case in edge_cases:
        X_case = pd.DataFrame([case["features"]], columns=feature_cols)
        pred = model.predict(X_case)[0]
        print(f"{case['name']}\n Predicted Impact Score: {pred:.4f}\n")

if __name__ == "__main__":
    evaluate()