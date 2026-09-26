"""
Runtime interface for the SATARK flood-impact ML model.

This module is the only runtime entry point required by the
flood-impact algorithm for model inference.

Canonical feature schema is defined in ml.features.
"""

from __future__ import annotations

import os
import sys
import warnings
from typing import Any, Mapping, Sequence

import joblib
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.features import (
    FLOOD_FEATURE_COLUMNS,
    normalize_flood_feature_dict,
    normalize_flood_feature_frame,
)

MODEL_PATH = os.path.join(PROJECT_ROOT, "ml", "flood_impact_model.joblib")

_MODEL_CACHE: dict[str, Any] = {}


def get_cached_model(model_path: str = MODEL_PATH) -> Any:
    """
    Load model once from disk and cache in memory for the process lifetime.
    Eliminates redundant disk I/O on initialization and counterfactual optimization passes.
    """
    if model_path not in _MODEL_CACHE:
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Flood impact model not found at {model_path}. Run ml/train.py first."
            )
        _MODEL_CACHE[model_path] = joblib.load(model_path)
    return _MODEL_CACHE[model_path]


def clear_model_cache() -> None:
    """Clear cached model instances (useful for testing or after retraining)."""
    _MODEL_CACHE.clear()


def warmup_model_cache(model_path: str = MODEL_PATH) -> bool:
    """
    Pre-warm model cache to ensure zero-latency initial scenario creation (<10ms).
    Returns True if model was successfully loaded/cached.
    """
    try:
        get_cached_model(model_path)
        return True
    except Exception:
        return False


class FloodImpactPredictor:
    """
    Runtime wrapper around the trained flood-impact model.

    Responsibilities:
        - load the trained model (via process singleton cache)
        - validate the feature schema
        - perform vectorized NumPy predictions
        - clamp predictions to [0, 1]

    This class does not:
        - simulate flooding
        - modify WorldState
        - simulate infrastructure
        - control agents
        - calculate risk
    """

    def __init__(
        self,
        model_path: str = MODEL_PATH,
        model: Any = None,
        use_cache: bool = True,
    ) -> None:
        self.model_path = model_path
        if model is not None:
            self.model = model
        elif use_cache:
            self.model = get_cached_model(model_path)
        else:
            if not os.path.exists(model_path):
                raise FileNotFoundError(
                    f"Flood impact model not found at {model_path}. Run ml/train.py first."
                )
            self.model = joblib.load(model_path)

    # ------------------------------------------------------------------
    # Public prediction API
    # ------------------------------------------------------------------

    def predict_features_matrix(self, X: np.ndarray) -> np.ndarray:
        """
        Fast vectorized inference directly on a 2D NumPy array of shape (N, len(FLOOD_FEATURE_COLUMNS)).
        Avoids all DataFrame creation, dictionary conversions, and re-validations.
        """
        if X.ndim != 2 or X.shape[1] != len(FLOOD_FEATURE_COLUMNS):
            raise ValueError(
                f"Expected feature matrix of shape (N, {len(FLOOD_FEATURE_COLUMNS)}), got {X.shape}"
            )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=UserWarning)
            predictions = self.model.predict(X)

        return np.clip(predictions, 0.0, 1.0)

    def predict_impact(
        self,
        features_dict: Mapping[str, Any],
    ) -> float:
        """
        Predict flood impact for one zone.
        """
        normalized = normalize_flood_feature_dict(features_dict)
        X = np.empty((1, len(FLOOD_FEATURE_COLUMNS)), dtype=np.float64)
        for j, col in enumerate(FLOOD_FEATURE_COLUMNS):
            X[0, j] = float(normalized[col])

        return float(self.predict_features_matrix(X)[0])

    def batch_predict(
        self,
        zones_feature_list: Sequence[Mapping[str, Any]],
    ) -> list[float]:
        """
        Takes a sequence of feature dictionaries for batch prediction.
        Populates a pre-allocated 2D NumPy array directly without intermediate DataFrames.
        """
        if not zones_feature_list:
            return []

        n_rows = len(zones_feature_list)
        n_cols = len(FLOOD_FEATURE_COLUMNS)
        X = np.empty((n_rows, n_cols), dtype=np.float64)

        for i, row in enumerate(zones_feature_list):
            normalized = normalize_flood_feature_dict(row)
            for j, col in enumerate(FLOOD_FEATURE_COLUMNS):
                X[i, j] = float(normalized[col])

        predictions = self.predict_features_matrix(X)
        return predictions.tolist()


if __name__ == "__main__":
    predictor = FloodImpactPredictor()

    test_zone = {
        "elevation": 0.2,
        "flood_exposure": 0.85,
        "severity": 3,
        "day": 5,
        "intervention": 0.10,
        "drainage_capacity": 0.25,
        "drainage_weakness": 0.75,
        "infra_vuln": 0.60,
        "pipe_surcharge": 0.50,
    }

    score = predictor.predict_impact(test_zone)
    print(f"Test Predicted Impact Score: {score:.3f}")