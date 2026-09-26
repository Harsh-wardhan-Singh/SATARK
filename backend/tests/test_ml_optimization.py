from __future__ import annotations

import os
from pathlib import Path
import numpy as np
import pytest

from ml.features import (
    FLOOD_FEATURE_COLUMNS,
    build_flood_feature_row,
    normalize_flood_feature_dict,
    zone_to_flood_features,
)
from ml.predict import (
    FloodImpactPredictor,
    get_cached_model,
    clear_model_cache,
    MODEL_PATH,
)
from algorithms.flood.impact import FloodImpactEngine


def test_model_compressed_file_size():
    """Verify that the trained model file size is compressed below 5 MB."""
    assert os.path.exists(MODEL_PATH), f"Model file missing at {MODEL_PATH}"
    size_bytes = os.path.getsize(MODEL_PATH)
    size_mb = size_bytes / (1024 * 1024)
    # Target was < 5 MB (reduced from 35.9 MB)
    assert size_mb < 5.0, f"Model size {size_mb:.2f} MB exceeds 5.0 MB threshold"
    assert size_mb > 0.5, f"Model size {size_mb:.2f} MB abnormally small"


def test_singleton_model_cache():
    """Verify that get_cached_model returns the identical in-memory instance."""
    clear_model_cache()
    m1 = get_cached_model(MODEL_PATH)
    m2 = get_cached_model(MODEL_PATH)
    assert m1 is m2, "Singleton cache failed to return the identical object"

    p1 = FloodImpactPredictor(use_cache=True)
    p2 = FloodImpactPredictor(use_cache=True)
    assert p1.model is p2.model, "FloodImpactPredictor instances did not share cached model"


def test_pure_numpy_matrix_equivalence():
    """Verify pure NumPy matrix prediction produces identical values to batch_predict."""
    predictor = FloodImpactPredictor()

    test_rows = [
        {
            "elevation": 0.2,
            "flood_exposure": 0.8,
            "severity": 3,
            "day": 4,
            "intervention": 0.2,
            "drainage_capacity": 0.4,
            "drainage_weakness": 0.6,
            "infra_vuln": 0.7,
            "pipe_surcharge": 0.5,
        },
        {
            "elevation": 0.8,
            "flood_exposure": 0.1,
            "severity": 1,
            "day": 1,
            "intervention": 0.9,
            "drainage_capacity": 0.8,
            "drainage_weakness": 0.2,
            "infra_vuln": 0.2,
            "pipe_surcharge": 0.0,
        },
    ]

    # Predict via batch_predict (mapping-based)
    batch_preds = predictor.batch_predict(test_rows)

    # Predict via direct NumPy matrix
    X = np.empty((len(test_rows), len(FLOOD_FEATURE_COLUMNS)), dtype=np.float64)
    for i, row in enumerate(test_rows):
        for j, col in enumerate(FLOOD_FEATURE_COLUMNS):
            X[i, j] = float(row[col])

    matrix_preds = predictor.predict_features_matrix(X)

    np.testing.assert_allclose(batch_preds, matrix_preds, rtol=1e-5)
    assert all(0.0 <= p <= 1.0 for p in matrix_preds)


def test_flood_impact_engine_vectorized_and_surcharge():
    """Verify FloodImpactEngine correctly integrates drainage surcharge in pure NumPy."""
    engine = FloodImpactEngine()

    flood_states = {
        "Z01": 0.6,
        "Z02": 0.6,
    }
    # Identical zones except one has surcharging drainage
    zones_data = {
        "Z01": {"elevation": 0.3, "drainage_capacity": 0.5, "infra_vuln": 0.5},
        "Z02": {"elevation": 0.3, "drainage_capacity": 0.5, "infra_vuln": 0.5},
    }

    drainage_state = {
        "zone_drainage": {
            "Z01": {"surcharge_rate": 0.0, "is_surcharging": False, "pipe_utilization": 0.4},
            "Z02": {"surcharge_rate": 1.8, "is_surcharging": True, "pipe_utilization": 1.5},
        }
    }

    impacts = engine.calculate_impacts(
        flood_states,
        zones_data,
        severity=2,
        day=3,
        intervention_level=0.2,
        drainage_state=drainage_state,
    )

    assert "Z01" in impacts and "Z02" in impacts
    assert 0.0 <= impacts["Z01"] <= 1.0
    assert 0.0 <= impacts["Z02"] <= 1.0
    # Z02 suffers pipe surcharge, so its impact must be strictly higher than Z01
    assert impacts["Z02"] > impacts["Z01"], (
        f"Expected surcharging zone Z02 ({impacts['Z02']}) to exceed Z01 ({impacts['Z01']})"
    )


def test_batch_inference_speed():
    """Verify that 21-zone vectorized batch prediction runs in under 20 ms."""
    import time

    engine = FloodImpactEngine()
    flood_states = {f"Z{i:02d}": 0.5 for i in range(1, 22)}
    zones_data = {
        f"Z{i:02d}": {"elevation": 0.3, "drainage_capacity": 0.6, "infra_vuln": 0.4}
        for i in range(1, 22)
    }

    # Warmup
    engine.calculate_impacts(flood_states, zones_data, severity=2, day=3, intervention_level=0.5)

    t0 = time.perf_counter()
    iterations = 50
    for _ in range(iterations):
        engine.calculate_impacts(flood_states, zones_data, severity=2, day=3, intervention_level=0.5)
    elapsed_ms = (time.perf_counter() - t0) * 1000 / iterations

    # Vectorized inference for 21 zones should be well under 20 ms
    assert elapsed_ms < 20.0, f"Average inference took {elapsed_ms:.2f} ms (expected < 20 ms)"
