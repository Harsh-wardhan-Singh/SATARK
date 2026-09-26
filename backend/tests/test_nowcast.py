from __future__ import annotations

from pathlib import Path
import pytest
from rest_framework.test import APIClient

from algorithms.flood.propagation import FloodPropagator
from algorithms.rainfall.hyetograph import HyetographEngine, HyetographType
from algorithms.rainfall.nowcast import NowcastEngine
from core.enums import CalamityType
from core.types import SimulationConfig
from simulation.engine import SimulationEngine
from simulation.scenario import Scenario


@pytest.fixture
def zone_mapping_path() -> Path:
    p = Path(__file__).resolve().parent.parent / "data" / "glb_zone_mapping.json"
    assert p.exists(), f"Zone mapping file not found at {p}"
    return p


@pytest.fixture
def flood_scenario(zone_mapping_path: Path) -> Scenario:
    data_dir = zone_mapping_path.parent
    config = SimulationConfig(
        duration=10800.0,
        tick_rate=1.0,
        calamity_type=CalamityType.FLOOD,
        random_seed=42,
    )
    return Scenario(
        config=config,
        parameters={
            "zone_mapping_path": str(zone_mapping_path),
            "infrastructure_path": str(data_dir / "infrastructure.json"),
            "shelters_path": str(data_dir / "shelters.json"),
            "population_path": str(data_dir / "population.json"),
            "rainfall_intensity": 50.0,
            "hyetograph_type": "CHICAGO",
            "peak_ratio": 0.4,
            "base_rainfall_intensity": 10.0,
        },
    )


# ==============================================================================
# 1. Hyetograph Tests
# ==============================================================================

def test_hyetograph_constant() -> None:
    engine = HyetographEngine(
        hyetograph_type=HyetographType.CONSTANT,
        peak_intensity=40.0,
        duration_seconds=3600.0,
    )
    assert engine.get_intensity(0.0) == 40.0
    assert engine.get_intensity(1800.0) == 40.0
    assert engine.get_intensity(3600.0) == 40.0
    # Decays after storm ends
    assert 0.0 < engine.get_intensity(4500.0) < 40.0


def test_hyetograph_chicago() -> None:
    duration = 7200.0  # 2 hours
    engine = HyetographEngine(
        hyetograph_type=HyetographType.CHICAGO,
        peak_intensity=60.0,
        duration_seconds=duration,
        peak_ratio=0.375,
        base_intensity=10.0,
    )
    tp = duration * 0.375  # 2700s

    # Intensity at peak should be approximately peak_intensity
    peak_val = engine.get_intensity(tp)
    assert abs(peak_val - 60.0) < 0.5, f"Expected peak near 60.0, got {peak_val}"

    # Pre-peak should be rising
    val_early = engine.get_intensity(600.0)
    val_mid = engine.get_intensity(1800.0)
    assert val_early < val_mid <= peak_val

    # Post-peak should be falling
    val_late = engine.get_intensity(4500.0)
    assert val_late < peak_val

    # Values must remain within [base_intensity, peak_intensity]
    for t in [0.0, 1000.0, 2700.0, 5000.0, 7200.0]:
        val = engine.get_intensity(t)
        assert 9.9 <= val <= 60.5


def test_hyetograph_scs_type_ii() -> None:
    duration = 3600.0
    engine = HyetographEngine(
        hyetograph_type=HyetographType.SCS_TYPE_II,
        peak_intensity=70.0,
        duration_seconds=duration,
        base_intensity=5.0,
    )
    # Peak is centered at tau = 0.5 (1800s)
    val_peak = engine.get_intensity(1800.0)
    assert abs(val_peak - 70.0) < 0.1

    # Symmetric points should have equal intensity
    val_early = engine.get_intensity(900.0)
    val_late = engine.get_intensity(2700.0)
    assert abs(val_early - val_late) < 0.01
    assert val_early < val_peak


def test_hyetograph_radar_and_profile() -> None:
    radar_data = [(0.0, 15.0), (1800.0, 55.0), (3600.0, 20.0)]
    engine = HyetographEngine(
        hyetograph_type=HyetographType.RADAR_NOWCAST,
        radar_series=radar_data,
        duration_seconds=3600.0,
    )
    assert engine.get_intensity(0.0) == 15.0
    assert engine.get_intensity(1800.0) == 55.0
    assert engine.get_intensity(3600.0) == 20.0
    # Interpolated midpoint: at 900s, expect (15+55)/2 = 35
    assert abs(engine.get_intensity(900.0) - 35.0) < 0.01

    # Profile generation
    profile = engine.get_profile(total_seconds=3600.0, step_seconds=900.0)
    assert len(profile) == 5  # 0, 900, 1800, 2700, 3600
    assert profile[0]["time_seconds"] == 0.0
    assert profile[0]["intensity"] == 15.0


# ==============================================================================
# 2. NowcastEngine State Isolation & Projection Tests
# ==============================================================================

def test_nowcast_engine_isolation(zone_mapping_path: Path) -> None:
    propagator = FloodPropagator(zone_mapping_path)
    # Pre-flood Z01 with 0.5m water
    propagator.water_depths[0] = 0.5
    propagator._sync_state_dict()

    initial_z01_cm = propagator.get_water_levels_cm()["Z01"]
    assert initial_z01_cm == 50.0

    hyetograph = HyetographEngine(
        hyetograph_type=HyetographType.CONSTANT,
        peak_intensity=0.1,  # 0.1 m/hr
        duration_seconds=10800.0,
    )

    nowcast_engine = NowcastEngine(propagator, hyetograph)
    result = nowcast_engine.generate_nowcast(
        current_simulation_time=0.0,
        horizons_hours=[1.0, 2.0, 3.0],
    )

    assert result["status"] == "SUCCESS"
    assert result["current_simulation_time"] == 0.0
    assert result["baseline_max_water_cm"] == 50.0
    assert len(result["horizons"]) == 3

    # CRITICAL: Verify base propagator was NOT mutated
    after_z01_cm = propagator.get_water_levels_cm()["Z01"]
    assert after_z01_cm == initial_z01_cm, (
        f"Base propagator state was mutated during nowcast! "
        f"Before: {initial_z01_cm}, After: {after_z01_cm}"
    )

    # Horizons must be strictly ordered
    h1 = result["horizons"][0]
    h2 = result["horizons"][1]
    h3 = result["horizons"][2]
    assert h1["horizon_hours"] == 1.0
    assert h2["horizon_hours"] == 2.0
    assert h3["horizon_hours"] == 3.0

    # Each horizon contains all 21 zones
    for h in [h1, h2, h3]:
        assert len(h["water_levels_cm"]) == 21
        assert len(h["delta_depths_cm"]) == 21
        assert h["severity_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


# ==============================================================================
# 3. SimulationEngine & Pipeline Integration Tests
# ==============================================================================

def test_simulation_engine_nowcast_method(flood_scenario: Scenario) -> None:
    engine = SimulationEngine(scenario=flood_scenario)
    engine.initialize()

    assert engine.hyetograph is not None
    assert engine.hyetograph.hyetograph_type == HyetographType.CHICAGO

    # Advance engine by a few ticks
    for _ in range(5):
        engine.step()

    forecast = engine.generate_nowcast(horizons_hours=[1.0, 2.0, 3.0])
    assert forecast["status"] == "SUCCESS"
    assert len(forecast["horizons"]) == 3
    assert forecast["hyetograph"]["hyetograph_type"] == "CHICAGO"
    assert "summary" in forecast
    assert "peak_projected_water_cm" in forecast["summary"]
    assert "overall_trend" in forecast["summary"]


# ==============================================================================
# 4. REST API Endpoint Tests
# ==============================================================================

def test_nowcast_api_endpoint(flood_scenario: Scenario) -> None:
    import api.views
    api.views._active_engine = None  # Ensure clean isolation
    client = APIClient()

    # 1. Uninitialized state returns 404
    resp_uninit = client.get("/api/simulation/nowcast/")
    # If no simulation is initialized, it should return 404
    assert resp_uninit.status_code in (404, 400)

    # 2. Initialize simulation
    init_payload = {
        "calamity_type": "FLOOD",
        "rainfall_intensity": 45.0,
        "duration": 7200.0,
        "tick_rate": 1.0,
    }
    init_resp = client.post("/api/simulation/initialize/", init_payload, format="json")
    assert init_resp.status_code in (200, 201)

    # 3. Call GET /api/simulation/nowcast/
    resp = client.get("/api/simulation/nowcast/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert "horizons" in data
    assert len(data["horizons"]) == 3
    assert "summary" in data

    # 4. Call with custom horizons parameter
    resp_custom = client.get("/api/simulation/nowcast/?horizons=0.5,1.5")
    assert resp_custom.status_code == 200
    custom_data = resp_custom.json()
    assert len(custom_data["horizons"]) == 2
    assert custom_data["horizons"][0]["horizon_hours"] == 0.5
    assert custom_data["horizons"][1]["horizon_hours"] == 1.5
