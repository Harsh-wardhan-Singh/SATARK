import pandas as pd
import joblib
import numpy as np
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
MODEL_PATH = os.path.join(PROJECT_ROOT, 'ml', 'flood_impact_model.joblib')

from ml.features import FLOOD_FEATURE_COLUMNS


def get_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model missing at {MODEL_PATH}. Train first.")
    return joblib.load(MODEL_PATH)


def test_ml_bounds_safety():
    """Ensure predictions remain within [0.0, 1.0] across randomized inputs."""
    print("Testing ML Boundary Safety (Ensuring no impossible impact scores)...")
    model = get_model()
    np.random.seed(42)

    elevations = np.random.uniform(0.0, 1.0, 500)
    drainage_cap = np.random.uniform(0.1, 0.9, 500)
    X_test = pd.DataFrame({
        "elevation": elevations,
        "flood_exposure": 1.0 - elevations,
        "severity": np.random.choice([1, 2, 3], 500),
        "day": np.random.randint(1, 8, 500),
        "intervention": np.random.uniform(0.0, 1.0, 500),
        "drainage_capacity": drainage_cap,
        "drainage_weakness": 1.0 - drainage_cap,
        "infra_vuln": np.random.uniform(0.0, 1.0, 500),
        "pipe_surcharge": np.random.uniform(0.0, 1.0, 500),
    })[FLOOD_FEATURE_COLUMNS]

    preds = model.predict(X_test)

    assert np.max(preds) <= 1.0, f"Upper bound violated: {np.max(preds)}"
    assert np.min(preds) >= 0.0, f"Lower bound violated: {np.min(preds)}"
    print(f"✅ Bounds Test Passed! (Min: {np.min(preds):.4f}, Max: {np.max(preds):.4f})")


def test_intervention_reduces_impact():
    """Verify high intervention strictly lowers impact under identical conditions."""
    print("Testing Intervention Logic (Ensuring rescues actually help)...")
    model = get_model()

    base_no_int_dict = {
        "elevation": 0.1,
        "flood_exposure": 0.9,
        "severity": 3,
        "day": 5,
        "intervention": 0.0,
        "drainage_capacity": 0.2,
        "drainage_weakness": 0.8,
        "infra_vuln": 0.8,
        "pipe_surcharge": 0.5,
    }
    base_max_int_dict = {
        "elevation": 0.1,
        "flood_exposure": 0.9,
        "severity": 3,
        "day": 5,
        "intervention": 1.0,
        "drainage_capacity": 0.2,
        "drainage_weakness": 0.8,
        "infra_vuln": 0.8,
        "pipe_surcharge": 0.5,
    }

    base_no_intervention = pd.DataFrame([base_no_int_dict])[FLOOD_FEATURE_COLUMNS]
    base_max_intervention = pd.DataFrame([base_max_int_dict])[FLOOD_FEATURE_COLUMNS]

    impact_no_int = model.predict(base_no_intervention)[0]
    impact_max_int = model.predict(base_max_intervention)[0]

    assert impact_max_int < impact_no_int, f"Intervention failed to reduce impact: {impact_max_int} >= {impact_no_int}"
    print(f"✅ Logic Test Passed! (Impact dropped from {impact_no_int:.4f} to {impact_max_int:.4f})")

if __name__ == "__main__":
    print("--- STARTING UNIT TESTS ---\n")
    try:
        test_ml_bounds_safety()
        print("-" * 30)
        test_intervention_reduces_impact()
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n⚠️ SYSTEM ERROR: {e}")