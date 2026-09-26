"""
Unit tests for Phase 8: Synthetic Metro Scenario Presets & Municipal Ward Localization.
Tests scenario presets API, Mumbai 2005 cloudburst hyetograph calibration,
and municipal ward identity metadata propagation.
"""

import json
from pathlib import Path
import pytest
from rest_framework.test import APIRequestFactory

from api.views import (
    SimulationPresetsView,
    WorldZonesView,
    SimulationInitializeView,
    SimulationStepView,
)
from algorithms.rainfall.hyetograph import (
    HyetographEngine,
    HyetographType,
    create_mumbai_2005_hyetograph,
)


@pytest.fixture
def factory():
    return APIRequestFactory()


def test_simulation_presets_endpoint(factory):
    """
    Test GET /api/simulation/presets/ returns all standardized disaster presets.
    """
    view = SimulationPresetsView.as_view()
    request = factory.get("/api/simulation/presets/")
    response = view(request)

    assert response.status_code == 200
    data = response.data
    assert data["status"] == "SUCCESS"
    assert data["count"] >= 3

    presets = {p["id"]: p for p in data["presets"]}
    assert "standard_monsoon" in presets
    assert "severe_flash_flood" in presets
    assert "mumbai_2005_cloudburst" in presets

    mumbai = presets["mumbai_2005_cloudburst"]
    assert mumbai["hyetograph_type"] == "MUMBAI_2005_CLOUDBURST"
    assert mumbai["rainfall_intensity"] >= 190.0
    assert mumbai["target_zone"] == "Z04"
    assert "Mithi" in mumbai["target_ward"]
    assert mumbai["duration_days"] == 1


def test_mumbai_2005_cloudburst_hyetograph_calibration():
    """
    Test the calibrated Mumbai 26 July 2005 storm hyetograph:
    - Peak intensity >= 180 mm/h around hour 15.5
    - Integrated total cumulative rainfall ~944 mm over 24 hours (within 1%)
    """
    hyeto = create_mumbai_2005_hyetograph()
    assert hyeto.hyetograph_type == HyetographType.MUMBAI_2005_CLOUDBURST
    assert hyeto.duration_seconds == 86400.0

    # Numerical integration using trapezoidal rule with 1-minute steps (1440 steps)
    dt_seconds = 60.0
    num_steps = int(86400.0 / dt_seconds)
    total_mm = 0.0

    peak_intensity = 0.0
    peak_time_hours = 0.0

    for i in range(num_steps):
        t = i * dt_seconds
        intensity = hyeto.get_intensity(t)
        assert intensity >= 0.0, f"Intensity cannot be negative at t={t}"
        if intensity > peak_intensity:
            peak_intensity = intensity
            peak_time_hours = t / 3600.0

        # intensity is mm/hr; dt is in seconds -> mm = intensity * (dt / 3600)
        total_mm += intensity * (dt_seconds / 3600.0)

    # Historical Mumbai 26 July benchmark: 944 mm
    assert 930.0 <= total_mm <= 960.0, f"Expected ~944mm total rainfall, got {total_mm:.1f}mm"
    assert peak_intensity >= 180.0, f"Expected peak >= 180 mm/h, got {peak_intensity:.1f} mm/h"
    assert 14.5 <= peak_time_hours <= 16.5, f"Peak should be between hours 14.5 and 16.5, got {peak_time_hours}"


def test_world_zones_ward_metadata_integrity(factory):
    """
    Test GET /api/world/zones/ propagates municipal ward identities for all 21 zones.
    """
    view = WorldZonesView.as_view()
    request = factory.get("/api/world/zones/")
    response = view(request)

    assert response.status_code == 200
    zones = response.data.get("zones", [])
    assert len(zones) == 21

    zone_map = {z["id"]: z for z in zones}

    # Verify every single zone has required ward metadata
    for zid, z in zone_map.items():
        assert "ward_code" in z, f"Zone {zid} missing ward_code"
        assert "ward_name" in z, f"Zone {zid} missing ward_name"
        assert "risk_classification" in z, f"Zone {zid} missing risk_classification"
        assert "primary_land_use" in z, f"Zone {zid} missing primary_land_use"
        assert z["ward_code"].startswith("Ward "), f"Zone {zid} ward_code invalid: {z['ward_code']}"

    # Verify landmark coastal municipal wards
    assert zone_map["Z01"]["ward_code"] == "Ward A"
    assert "Colaba" in zone_map["Z01"]["ward_name"]

    assert zone_map["Z04"]["ward_code"] == "Ward H/E"
    assert "BKC" in zone_map["Z04"]["ward_name"]
    assert "Critical" in zone_map["Z04"]["risk_classification"]

    assert zone_map["Z09"]["ward_code"] == "Ward G/N"
    assert "Dharavi" in zone_map["Z09"]["ward_name"]

    assert zone_map["Z10"]["ward_code"] == "Ward F/N"
    assert "Matunga" in zone_map["Z10"]["ward_name"]


def test_simulation_run_with_mumbai_cloudburst_preset(factory):
    """
    Test initializing and stepping a simulation using the Mumbai 2005 cloudburst preset.
    """
    init_view = SimulationInitializeView.as_view()
    init_payload = {
        "duration": 86400.0,
        "tick_rate": 1.0 / 3600.0,
        "calamity_type": "FLOOD",
        "parameters": {
            "representative_agent_count": 100,
            "severity": 3,
            "rainfall_intensity": 190.3,
            "hyetograph_type": "MUMBAI_2005_CLOUDBURST",
            "zone_id": "Z04",
        },
    }

    req = factory.post("/api/simulation/initialize/", init_payload, format="json")
    resp = init_view(req)
    assert resp.status_code in (200, 201)
    assert resp.data["simulation"]["initialized"] is True

    # Step simulation multiple ticks (hours)
    step_view = SimulationStepView.as_view()
    for _ in range(3):
        step_req = factory.post("/api/simulation/step/", {"steps": 1}, format="json")
        step_resp = step_view(step_req)
        assert step_resp.status_code == 200

    # Verify simulation state reflects active simulation progress
    assert step_resp.data["simulationTime"] > 0
    assert step_resp.data["currentTick"] >= 3
