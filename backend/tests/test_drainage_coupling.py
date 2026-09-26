from pathlib import Path
import pytest

from algorithms.drainage import (
    CoupledDrainageModel,
    DrainageNetwork,
    ZoneDrainageSummary,
    DrainageStepResult,
)


@pytest.fixture
def drainage_network():
    data_path = Path(__file__).resolve().parent.parent / "data" / "drainage_network.json"
    if not data_path.exists():
        pytest.skip("drainage_network.json not found")
    return DrainageNetwork.from_file(str(data_path))


def test_coupled_model_initialization(drainage_network):
    model = CoupledDrainageModel(network=drainage_network)
    assert model.network is not None
    assert len(model.network.nodes) == 34
    assert len(model.network.pipes) == 33


def test_coupled_step_dry_surface(drainage_network):
    model = CoupledDrainageModel(network=drainage_network)
    water_levels = {f"Z{i:02d}": 0.0 for i in range(1, 22)}
    result = model.step(water_levels=water_levels, delta_time=3600.0)

    assert isinstance(result, DrainageStepResult)
    assert result.total_intake_flow == 0.0
    assert result.total_surcharge_flow == 0.0
    for zone_id, summary in result.zone_summaries.items():
        assert isinstance(summary, ZoneDrainageSummary)
        assert summary.surface_intake_rate == 0.0
        assert summary.is_surcharging is False
        assert summary.drainage_weakness == 0.2


def test_coupled_step_surface_intake(drainage_network):
    model = CoupledDrainageModel(network=drainage_network)
    # Z01 has 0.15m water depth
    water_levels = {"Z01": 0.15}
    result = model.step(water_levels=water_levels, delta_time=3600.0)

    assert result.total_intake_flow > 0.0
    assert "Z01" in result.zone_summaries
    z01_sum = result.zone_summaries["Z01"]
    assert z01_sum.surface_intake_rate > 0.0
    assert z01_sum.net_drainage_rate > 0.0


def test_coupled_step_surcharge_detection(drainage_network):
    model = CoupledDrainageModel(network=drainage_network)
    # Flood all zones with extreme 5.0m water depth
    water_levels = {f"Z{i:02d}": 5.0 for i in range(1, 22)}
    result = model.step(water_levels=water_levels, delta_time=60.0)

    assert result.total_intake_flow > 0.0
    # Pipes should experience surcharge under extreme sudden inflow
    assert result.max_pipe_utilization > 0.5


def test_coupled_step_pump_boost(drainage_network):
    model = CoupledDrainageModel(network=drainage_network)
    water_levels = {"Z01": 1.0, "Z07": 1.0}

    # Baseline step without pump boost
    base_res = model.step(water_levels=water_levels, delta_time=120.0)

    # Step with pump boost on Z07 (where pump station node PS01 resides)
    boosted_res = model.step(
        water_levels=water_levels,
        delta_time=120.0,
        pump_boosts={"Z07": 10.0},
    )

    assert boosted_res.total_conveyed_flow >= base_res.total_conveyed_flow
    assert "Z07" in boosted_res.active_pump_boosts


def test_coupled_step_global_pump_boost(drainage_network):
    model = CoupledDrainageModel(network=drainage_network)
    water_levels = {"Z07": 2.0}

    res_normal = model.step(water_levels=water_levels, delta_time=60.0, global_pump_boost=0.0)
    res_boosted = model.step(water_levels=water_levels, delta_time=60.0, global_pump_boost=5.0)

    assert res_boosted.total_conveyed_flow >= res_normal.total_conveyed_flow
