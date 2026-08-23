"""Canonical flood ML feature contract."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

import pandas as pd


FLOOD_FEATURE_COLUMNS = [
    "elevation",
    "flood_exposure",
    "severity",
    "day",
    "intervention",
    "drainage_weakness",
    "infra_vuln",
]


def build_flood_feature_row(
    *,
    elevation: float,
    flood_exposure: float,
    severity: int,
    day: int,
    intervention: float,
    drainage_weakness: float,
    infra_vuln: float,
) -> dict[str, Any]:
    """
    Build one canonical flood feature row in the exact training order.
    """
    return {
        "elevation": float(elevation),
        "flood_exposure": float(flood_exposure),
        "severity": int(severity),
        "day": int(day),
        "intervention": float(intervention),
        "drainage_weakness": float(drainage_weakness),
        "infra_vuln": float(infra_vuln),
    }


def build_flood_feature_frame(rows: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """
    Build a DataFrame using the canonical flood ML columns.
    Raises if any required column is missing.
    """
    df = pd.DataFrame(list(rows))
    return normalize_flood_feature_frame(df)


def normalize_flood_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and reorder a DataFrame to match the canonical flood schema.
    """
    missing = [col for col in FLOOD_FEATURE_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing flood feature columns: {missing}")

    return df[FLOOD_FEATURE_COLUMNS].copy()


def normalize_flood_feature_dict(features: Mapping[str, Any]) -> dict[str, Any]:
    """
    Validate and reorder a single feature mapping.
    """
    missing = [col for col in FLOOD_FEATURE_COLUMNS if col not in features]
    if missing:
        raise ValueError(f"Missing flood feature keys: {missing}")

    return {col: features[col] for col in FLOOD_FEATURE_COLUMNS}


def zone_to_flood_features(
    zone_id: str,
    zone_data: Mapping[str, Any],
    *,
    water_level: float,
    severity: int,
    day: int,
    intervention: float,
) -> dict[str, Any]:
    """
    Convert zone metadata and current flood state into the canonical schema.
    """
    elevation = zone_data.get("elevation")
    if elevation is None:
        elevation = zone_data.get("center_normalized", {}).get("y", 0.5)

    drainage_capacity = zone_data.get("drainage_capacity", zone_data.get("drainage_rate", 0.5))
    infra_vuln = zone_data.get("infra_vuln", zone_data.get("infrastructure_vulnerability", 0.5))

    return build_flood_feature_row(
        elevation=elevation,
        flood_exposure=min(1.0, max(0.0, water_level / 2.0)),
        severity=severity,
        day=day,
        intervention=intervention,
        drainage_weakness=1.0 - float(drainage_capacity),
        infra_vuln=float(infra_vuln),
    )