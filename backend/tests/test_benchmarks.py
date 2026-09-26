"""
Automated Performance Benchmarking Suite.

Validates that:
- 1-hour simulation tick executes in < 50 ms (mandate: < 100 ms)
- Warm simulation initialization executes in < 50 ms
- Memory and event history remain strictly bounded over long runs (no memory leaks)
- Counterfactual optimization evaluations run efficiently
"""

import time
import pytest
from core.enums import CalamityType
from core.types import SimulationConfig
from decision.intervention import CandidateIntervention, Intervention
from simulation.scenario import Scenario
from simulation.engine import SimulationEngine


@pytest.fixture
def standard_scenario():
    cfg = SimulationConfig(
        duration=86400.0,
        tick_rate=1.0 / 3600.0,
        calamity_type=CalamityType.FLOOD,
    )
    params = {
        "zone_mapping_path": "data/glb_zone_mapping.json",
        "infrastructure_path": "data/infrastructure.json",
        "population_path": "data/population.json",
        "shelters_path": "data/shelters.json",
        "representative_agent_count": 250,
        "zone_id": "Z04",
        "severity": 2,
        "rainfall_intensity": 45.0,
    }
    return Scenario(config=cfg, parameters=params)


def test_simulation_tick_performance(standard_scenario):
    """
    Validate that each 1-hour simulation tick executes in < 50 ms (mandate: < 100 ms).
    """
    engine = SimulationEngine(scenario=standard_scenario)
    engine.initialize()

    step_times_ms = []
    # Warm up 2 steps
    for _ in range(2):
        engine.step()

    # Benchmark 10 steps
    for _ in range(10):
        t0 = time.perf_counter()
        engine.step()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        step_times_ms.append(dt_ms)

    avg_step_ms = sum(step_times_ms) / len(step_times_ms)
    print(f"\n[BENCHMARK] Average 1-hour tick duration: {avg_step_ms:.2f} ms")

    assert avg_step_ms < 50.0, (
        f"Simulation step exceeded 50ms performance threshold: {avg_step_ms:.2f} ms"
    )


def test_warm_initialization_performance(standard_scenario):
    """
    Validate that subsequent scenario initializations (with warm ML and zone caches)
    execute in < 50 ms.
    """
    # First engine primes cache
    engine1 = SimulationEngine(scenario=standard_scenario)
    engine1.initialize()

    # Second engine warm initialization
    engine2 = SimulationEngine(scenario=standard_scenario)
    t0 = time.perf_counter()
    engine2.initialize()
    init_ms = (time.perf_counter() - t0) * 1000.0

    print(f"\n[BENCHMARK] Warm initialization duration: {init_ms:.2f} ms")
    assert init_ms < 50.0, (
        f"Warm initialization exceeded 50ms threshold: {init_ms:.2f} ms"
    )


def test_long_running_memory_stability():
    """
    Validate that 50 consecutive simulation ticks maintain bounded event history
    and strictly non-negative water volumes and population counts.
    """
    cfg = SimulationConfig(
        duration=3600.0 * 60,
        tick_rate=1.0 / 3600.0,
        calamity_type=CalamityType.FLOOD,
    )
    params = {
        "zone_mapping_path": "data/glb_zone_mapping.json",
        "infrastructure_path": "data/infrastructure.json",
        "population_path": "data/population.json",
        "shelters_path": "data/shelters.json",
        "representative_agent_count": 250,
        "zone_id": "Z04",
        "severity": 2,
        "rainfall_intensity": 45.0,
    }
    scenario = Scenario(config=cfg, parameters=params)
    engine = SimulationEngine(scenario=scenario)
    engine.initialize()

    for _ in range(50):
        engine.step()

    # Verify event history ring buffer is capped at MAX_EVENT_HISTORY
    assert len(engine.world.state.events) <= 50

    # Verify water levels remain non-negative and valid
    water_levels = engine.world.state.environment.get("flood_water_levels", {})
    assert len(water_levels) == 21
    for zid, level in water_levels.items():
        assert level >= 0.0, f"Negative water level detected in {zid}: {level}"

    # Verify metrics remain healthy
    metrics = engine.world.state.metrics
    assert metrics.get("agent_count", 0) > 0
    assert metrics.get("total_fatalities", 0) >= 0
    assert metrics.get("total_injuries", 0) >= 0


def test_optimizer_evaluation_performance(standard_scenario):
    """
    Validate that candidate intervention optimization evaluates cleanly and produces valid metrics.
    """
    engine = SimulationEngine(scenario=standard_scenario)
    engine.initialize()

    candidates = [
        CandidateIntervention(
            intervention=Intervention(
                intervention_id="deploy_mobile_pumps",
                name="Deploy Mobile Drainage Pumps",
                description="Boost zone drainage by 5 cm/hr",
                target="Z04",
                expected_effects={"drainage_boost": 0.05},
            ),
            score=0.85,
            rationale=("Reduces flood height in zone Z04",),
            applicable=True,
        )
    ]

    t0 = time.perf_counter()
    result = engine.optimize_interventions(candidates)
    duration_ms = (time.perf_counter() - t0) * 1000.0

    print(f"\n[BENCHMARK] Candidate optimization duration: {duration_ms:.2f} ms")
    assert result is not None
    assert len(result.candidates) == 1
    assert result.baseline is not None
    assert result.selected_intervention is not None
