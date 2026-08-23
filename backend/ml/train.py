import pandas as pd
import os
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

def train_model():
    csv_path = os.path.join(PROJECT_ROOT, 'data', 'raw', 'flood_model_training.csv')
    df = pd.read_csv(csv_path)
    
    # Train on all structural parameters
    feature_cols = ['elevation', 'flood_exposure', 'severity', 'day', 'intervention', 'drainage_weakness', 'infra_vuln']
    X = df[feature_cols]
    y = df['impact_score']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    rf_model = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42)
    rf_model.fit(X_train, y_train)
    
    preds = rf_model.predict(X_test)
    print(f"Model Trained. MSE: {mean_squared_error(y_test, preds):.5f} | R2: {r2_score(y_test, preds):.4f}")
    
    model_path = os.path.join(SCRIPT_DIR, 'flood_impact_model.joblib')
    joblib.dump(rf_model, model_path)
    print(f"Model saved to: {model_path}")

if __name__ == "__main__":
    train_model()