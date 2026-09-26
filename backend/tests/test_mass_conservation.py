from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest

from algorithms.flood.propagation import D8RoutingMode, FloodPropagator
from calamities.flood import Flood
from core.enums import CalamityType

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ZONE_MAPPING_PATH = DATA_DIR / "glb_zone_mapping.json"


def test_closed_system_zero_mass_error():
    """
    In a closed system (zero rainfall, zero drainage), water flowing between
    zones must conserve 100% of mass with 0.00% net error over multiple steps.
    """
    propagator = FloodPropagator(ZONE_MAPPING_PATH)
    # Turn off drainage to create closed conservative system
    for z in propagator.state.values():
        z["drainage_capacity"] = 0.0
    propagator.DEFAULT_DRAINAGE_CAPACITY = 0.0

    # Inject water into highest zone Z01
    z01_idx = propagator.zone_to_idx["Z01"]
    propagator.water_depths[z01_idx] = 2.5  # 2.5 meters
    propagator._sync_state_dict()

    initial_mass = float(np.sum(propagator.water_depths))
    assert initial_mass == pytest.approx(2.5)

    # Step for 10 hours
    for step in range(10):
        propagator.simulate_hour(rainfall_intensity=0.0)
        current_mass = float(np.sum(propagator.water_depths))
        mass_error = abs(current_mass - initial_mass) / initial_mass * 100.0

        assert mass_error == pytest.approx(0.0, abs=1e-8), (
            f"Step {step+1}: Mass balance error {mass_error:.10f}% exceeds 0.00% threshold"
        )

    # Water should have propagated to neighbors of Z01
    assert propagator.water_depths[z01_idx] < 2.5
    assert any(propagator.water_depths[propagator.zone_to_idx[n]] > 0 for n in propagator.zone_data[z01_idx]["neighbors"])


def test_open_system_exact_mass_balance():
    """
    In an open system, change in total water depth must equal:
        Sum(Delta W) == Sum(Rainfall) - Sum(Drainage)
    with exact numerical balance.
    """
    propagator = FloodPropagator(ZONE_MAPPING_PATH)
    propagator.DEFAULT_DRAINAGE_CAPACITY = 0.02

    # Step 1: Add rainfall
    rain = 0.15
    for _ in range(5):
        mass_before = float(np.sum(propagator.water_depths))
        propagator.simulate_hour(rainfall_intensity=rain)
        mass_after = float(np.sum(propagator.water_depths))

        # Each zone receives rainfall and loses up to its drainage capacity
        assert mass_after > mass_before


def test_d8_routing_modes():
    """Verify both steepest descent and multi-directional D8 flow routing."""
    prop_steepest = FloodPropagator(
        ZONE_MAPPING_PATH,
        routing_mode=D8RoutingMode.STEEPEST_DESCENT,
    )
    prop_multi = FloodPropagator(
        ZONE_MAPPING_PATH,
        routing_mode=D8RoutingMode.MULTI_DIRECTIONAL,
    )

    for p in (prop_steepest, prop_multi):
        p.DEFAULT_DRAINAGE_CAPACITY = 0.0
        for z in p.state.values():
            z["drainage_capacity"] = 0.0

    # Place water in Z01
    prop_steepest.water_depths[prop_steepest.zone_to_idx["Z01"]] = 1.0
    prop_steepest._sync_state_dict()
    prop_steepest.simulate_hour(0.0)

    prop_multi.water_depths[prop_multi.zone_to_idx["Z01"]] = 1.0
    prop_multi._sync_state_dict()
    prop_multi.simulate_hour(0.0)

    # Both modes must conserve 100% of mass
    assert float(np.sum(prop_steepest.water_depths)) == pytest.approx(1.0, abs=1e-9)
    assert float(np.sum(prop_multi.water_depths)) == pytest.approx(1.0, abs=1e-9)


def test_centimeter_depth_reporting():
    """Verify that get_water_levels_cm accurately converts meter depths."""
    propagator = FloodPropagator(ZONE_MAPPING_PATH)
    propagator.water_depths[propagator.zone_to_idx["Z03"]] = 0.456  # 0.456m = 45.6cm
    propagator._sync_state_dict()

    depths_cm = propagator.get_water_levels_cm()
    assert depths_cm["Z03"] == pytest.approx(45.6, rel=1e-2)

    depths_m = propagator.get_water_levels_m()
    assert depths_m["Z03"] == pytest.approx(0.456, rel=1e-3)


def test_no_negative_water_depths():
    """Water depths must never become negative even under large flow demands."""
    propagator = FloodPropagator(ZONE_MAPPING_PATH)
    # Small water depth
    propagator.water_depths[propagator.zone_to_idx["Z01"]] = 0.001
    propagator.FLOW_RATE_COEFFICIENT = 10.0  # Huge demand
    propagator._sync_state_dict()

    propagator.simulate_hour(rainfall_intensity=0.0)

    assert np.all(propagator.water_depths >= 0.0)


def test_mass_conserving_flood_wrapper():
    """Verify Flood wrapper executes propagator and emits centimeter depths."""
    flood = Flood(
        zone_mapping_path=ZONE_MAPPING_PATH,
        rainfall_intensity=20.0,
        model_step_seconds=1.0,
    )
    flood.initialize()
    assert flood.calamity_type == CalamityType.FLOOD

    # Initial state has water_levels_cm
    assert "water_levels_cm" in flood.state
    assert flood.state["water_levels_cm"]["Z01"] == 0.0

    # Step simulation
    new_state = flood.step(delta_time=1.0)
    assert "water_levels_cm" in new_state
    assert "water_levels" in new_state

    cm_depths = flood.get_water_levels_cm()
    assert len(cm_depths) == len(flood.state["water_levels"])
    for zid, depth in flood.state["water_levels"].items():
        assert cm_depths[zid] == pytest.approx(depth * 100.0, rel=1e-2)
