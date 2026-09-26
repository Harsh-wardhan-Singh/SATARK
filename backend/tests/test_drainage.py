from __future__ import annotations

import math
from pathlib import Path

import pytest

from algorithms.drainage import (
    CoupledDrainageModel,
    DrainageNetwork,
    DrainageNode,
    DrainagePipe,
    ManningHydraulicsEngine,
    NodeType,
)
from core.enums import CalamityType
from core.types import SimulationConfig
from simulation.clock import SimulationClock
from simulation.pipeline.base_step import SimulationPipeline, StepContext
from simulation.pipeline.drainage_step import DrainageStep
from simulation.scenario import Scenario
from simulation.world import SimulationWorld

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DRAINAGE_JSON = DATA_DIR / "drainage_network.json"


def test_manning_formula_flow_capacity():
    """Verify Manning capacity formula against known analytical calculation."""
    # Diameter = 1.0 m, Slope = 0.002, Roughness = 0.013
    d = 1.0
    s = 0.002
    n = 0.013

    area = (math.pi * (d ** 2)) / 4.0  # 0.785398 m^2
    r_h = d / 4.0                      # 0.25 m
    expected_q = (1.0 / n) * area * (r_h ** (2.0 / 3.0)) * math.sqrt(s)

    computed_q = ManningHydraulicsEngine.calculate_pipe_capacity(
        diameter_m=d,
        slope=s,
        roughness=n,
    )

    assert computed_q == pytest.approx(expected_q, rel=1e-4)
    assert computed_q > 1.0  # ~1.071 m^3/s


def test_manning_invalid_parameters():
    """Verify Manning engine validates diameter and roughness."""
    with pytest.raises(ValueError):
        ManningHydraulicsEngine.calculate_pipe_capacity(diameter_m=0.0, slope=0.01)

    with pytest.raises(ValueError):
        ManningHydraulicsEngine.calculate_pipe_capacity(diameter_m=-1.0, slope=0.01)

    with pytest.raises(ValueError):
        ManningHydraulicsEngine.calculate_pipe_capacity(diameter_m=1.0, slope=0.01, roughness=0.0)


def test_manning_surcharge_evaluation():
    """Verify flow evaluation under sub-capacity and surcharge conditions."""
    capacity = 2.0  # m^3/s

    # Case 1: Inflow within capacity
    res1 = ManningHydraulicsEngine.evaluate_pipe_flow(inflow_m3_s=1.5, capacity_m3_s=capacity)
    assert res1.conveyed_flow == pytest.approx(1.5)
    assert res1.surcharge_flow == pytest.approx(0.0)
    assert res1.utilization == pytest.approx(0.75)
    assert not res1.is_surcharging

    # Case 2: Inflow exceeds capacity -> surcharge
    res2 = ManningHydraulicsEngine.evaluate_pipe_flow(inflow_m3_s=3.5, capacity_m3_s=capacity)
    assert res2.conveyed_flow == pytest.approx(2.0)
    assert res2.surcharge_flow == pytest.approx(1.5)
    assert res2.utilization == pytest.approx(1.0)
    assert res2.is_surcharging

    # Case 3: Mechanical pump boost increases capacity
    res3 = ManningHydraulicsEngine.evaluate_pipe_flow(
        inflow_m3_s=3.5,
        capacity_m3_s=capacity,
        pump_boost_m3_s=2.0,
    )
    assert res3.conveyed_flow == pytest.approx(3.5)
    assert res3.surcharge_flow == pytest.approx(0.0)
    assert not res3.is_surcharging


def test_drainage_network_loading():
    """Verify loading drainage_network.json produces valid graph topology."""
    assert DRAINAGE_JSON.exists(), f"Missing dataset: {DRAINAGE_JSON}"
    network = DrainageNetwork.from_file(DRAINAGE_JSON)

    assert len(network.nodes) >= 21
    assert len(network.pipes) >= 20

    # Ensure all 21 zones have associated inlet nodes
    for i in range(1, 22):
        zid = f"Z{i:02d}"
        inlets = network.get_inlets_for_zone(zid)
        assert len(inlets) >= 1, f"Zone {zid} must have at least one inlet"
        assert inlets[0].node_type == NodeType.INLET

    # Ensure pump stations and outfalls exist
    pumps = [n for n in network.nodes.values() if n.node_type == NodeType.PUMP_STATION]
    assert len(pumps) >= 3

    outfalls = [n for n in network.nodes.values() if n.node_type == NodeType.OUTFALL]
    assert len(outfalls) >= 3


def test_coupled_drainage_model_exchange():
    """Verify dual-layer surface-drainage exchange steps correctly."""
    network = DrainageNetwork.from_file(DRAINAGE_JSON)
    model = CoupledDrainageModel(network=network)

    # Moderate flood depths in high and mid zones
    water_levels = {
        "Z01": 0.5,
        "Z02": 0.3,
        "Z07": 0.4,
    }

    result = model.step(water_levels=water_levels, delta_time=1.0)

    assert result.total_intake_flow > 0.0
    assert result.total_conveyed_flow > 0.0
    assert len(result.zone_summaries) >= 21

    # Check Z01 summary
    z01_sum = result.zone_summaries["Z01"]
    assert z01_sum.surface_intake_rate > 0.0
    assert z01_sum.net_drainage_rate > 0.0
    assert 0.0 <= z01_sum.pipe_utilization <= 1.0


def test_pump_intervention_boosts_throughput():
    """Verify that pump interventions reduce surcharge and boost conveyance."""
    network = DrainageNetwork.from_file(DRAINAGE_JSON)
    model = CoupledDrainageModel(network=network)

    # Heavy flooding to trigger surcharge in collector zones
    heavy_floods = {f"Z{i:02d}": 1.5 for i in range(1, 22)}

    # Run baseline (no pump boost)
    res_baseline = model.step(water_levels=heavy_floods, delta_time=1.0)

    # Run with pump boost at low-lying pump station zone Z18
    res_boosted = model.step(
        water_levels=heavy_floods,
        delta_time=1.0,
        pump_boosts={"Z18": 3.0, "pump_P02": 2.0},
        global_pump_boost=1.5,
    )

    # Boosted conveyance should be greater or equal
    assert res_boosted.total_conveyed_flow >= res_baseline.total_conveyed_flow


def test_drainage_step_in_pipeline():
    """Verify DrainageStep executes within SimulationPipeline."""
    clock = SimulationClock(tick_rate=1.0)
    world = SimulationWorld()
    world.initialize(calamity_type=CalamityType.FLOOD)

    scenario = Scenario(
        config=SimulationConfig(
            duration=10.0,
            tick_rate=1.0,
            calamity_type=CalamityType.FLOOD,
        ),
    )

    network = DrainageNetwork.from_file(DRAINAGE_JSON)
    drainage_model = CoupledDrainageModel(network=network)

    context = StepContext(
        clock=clock,
        world=world,
        scenario=scenario,
        delta_time=1.0,
        drainage_model=drainage_model,
        flood_water_levels={"Z01": 0.8, "Z03": 0.5, "Z14": 0.9},
        active_interventions=[
            {
                "id": "deploy_mobile_pumps",
                "action": "deploy_mobile_pumps",
                "effect": {"drainage_rate_boost": 0.1},
                "target_zones": ["Z14"],
            }
        ],
    )

    pipeline = SimulationPipeline([DrainageStep()])
    pipeline.execute(context)

    # Verify context and world state mutations
    assert context.world.state.environment["drainage_boost"] == pytest.approx(0.1)
    assert "drainage" in context.world.state.environment
    drainage_env = context.world.state.environment["drainage"]
    assert drainage_env["total_intake_flow"] > 0.0
    assert "avg_pipe_utilization" in context.world.state.metrics
    assert any(e["type"] == "DRAINAGE_STEPPED" for e in context.world.state.events)
