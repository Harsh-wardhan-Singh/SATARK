"""
Runtime interface for the SATARK flood-impact ML model.

This module is the only runtime entry point required by the
flood-impact algorithm for model inference.

Canonical feature schema is defined in ml.features.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Sequence

import joblib
import numpy as np
import pandas as pd

from ml.features import (
    FLOOD_FEATURE_COLUMNS,
    normalize_flood_feature_dict,
    normalize_flood_feature_frame,
)


SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MODEL_PATH = os.path.join(
    SCRIPT_DIR,
    "flood_impact_model.joblib",
)


class FloodImpactPredictor:
    """
    Runtime wrapper around the trained flood-impact model.

    Responsibilities:
        - load the trained model
        - validate the feature schema
        - perform single predictions
        - perform batch predictions
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
    ) -> None:

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                "Flood impact model not found at "
                f"{model_path}. "
                "Run ml/train.py first."
            )

        self.model_path = model_path

        self.model = joblib.load(
            model_path
        )

        self._validate_model_schema()

    # ------------------------------------------------------------------
    # Public prediction API
    # ------------------------------------------------------------------

    def predict_impact(
        self,
        features_dict: Mapping[str, Any],
    ) -> float:
        """
        Predict flood impact for one zone.

        Expected features:

            elevation
            flood_exposure
            severity
            day
            intervention
            drainage_weakness
            infra_vuln

        Returns:
            Float impact score in [0, 1].
        """

        normalized_features = (
            self._normalize_feature_dict(
                features_dict
            )
        )

        df = pd.DataFrame(
            [normalized_features],
            columns=FLOOD_FEATURE_COLUMNS,
        )

        prediction = self.model.predict(
            df
        )[0]

        return self._clip_prediction(
            prediction
        )

    def batch_predict(
        self,
        zones_feature_list: Sequence[
            Mapping[str, Any]
        ],
    ) -> list[float]:
        """
        Predict flood impact for multiple zones.

        Every dictionary must contain exactly the
        canonical flood feature set.
        """

        if not zones_feature_list:
            return []

        normalized_rows = [
            self._normalize_feature_dict(
                features
            )
            for features in zones_feature_list
        ]

        df = pd.DataFrame(
            normalized_rows,
            columns=FLOOD_FEATURE_COLUMNS,
        )

        predictions = self.model.predict(
            df
        )

        return [
            self._clip_prediction(
                prediction
            )
            for prediction in predictions
        ]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_feature_dict(
        features: Mapping[str, Any],
    ) -> dict[str, Any]:
        """
        Validate and normalize one feature dictionary.

        Missing and unexpected fields are rejected so an old or
        incompatible schema cannot silently reach the model.
        """

        expected = set(
            FLOOD_FEATURE_COLUMNS
        )

        received = set(
            features.keys()
        )

        missing = expected - received
        unexpected = received - expected

        if missing:
            raise ValueError(
                "Missing flood feature keys: "
                f"{sorted(missing)}"
            )

        if unexpected:
            raise ValueError(
                "Unexpected flood feature keys: "
                f"{sorted(unexpected)}"
            )

        return normalize_flood_feature_dict(
            features
        )

    def _validate_model_schema(
        self,
    ) -> None:
        """
        Verify that the loaded model uses the canonical
        training feature schema.

        scikit-learn models trained using a pandas DataFrame
        expose feature_names_in_.
        """

        model_features = getattr(
            self.model,
            "feature_names_in_",
            None,
        )

        if model_features is None:
            return

        model_features = [
            str(feature)
            for feature in model_features
        ]

        expected_features = (
            FLOOD_FEATURE_COLUMNS
        )

        if model_features != expected_features:
            raise ValueError(
                "Flood ML model feature schema mismatch.\n"
                f"Expected: {expected_features}\n"
                f"Model:    {model_features}"
            )

    @staticmethod
    def _clip_prediction(
        prediction: Any,
    ) -> float:
        """
        Clamp model output to the SATARK impact range [0, 1].
        """

        return float(
            np.clip(
                float(prediction),
                0.0,
                1.0,
            )
        )