from __future__ import annotations

from pathlib import Path
import pytest

from core.enums import CalamityType
from core.types import SimulationConfig
from simulation.clock import SimulationClock
from simulation.scenario import Scenario
from simulation.world import SimulationWorld
from simulation.pipeline.base_step import SimulationPipeline, StepContext
from simulation.pipeline.rainfall_step import RainfallStep
from simulation.pipeline.drainage_step import DrainageStep
from simulation.pipeline.surface_step import SurfaceFloodStep
from simulation.pipeline.impact_step import FloodImpactStep
from simulation.pipeline.cascade_step import InfrastructureCascadeStep
from simulation.pipeline.evacuation_step import HumanEvacuationStep
from simulation.pipeline.risk_step import RiskAssessmentStep
from simulation.pipeline.decision_step import DecisionInterventionStep
from simulation.pipeline.metrics_step import MetricsStep
from algorithms.intervention.recommendations import InterventionRuleEngine

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def test_context():
    config = SimulationConfig(
        duration=3600.0,
        tick_rate=1.0,
        calamity_type=CalamityType.FLOOD,
        random_seed=42,
    )
    scenario = Scenario(
        config=config,
        parameters={
            "rainfall_intensity": 50.0,
            "zone_mapping_path": str(DATA_DIR / "glb_zone_mapping.json"),
            "infrastructure_path": str(DATA_DIR / "infrastructure.json"),
            "shelters_path": str(DATA_DIR / "shelters.json"),
            "population_path": str(DATA_DIR / "population.json"),
        },
    )
    clock = SimulationClock(tick_rate=1.0)
    world = SimulationWorld()
    world.initialize(scenario)

    return StepContext(
        clock=clock,
        world=world,
        scenario=scenario,
        delta_time=1.0,
        intervention_rule_engine=InterventionRuleEngine(),
    )


def test_rainfall_step(test_context):
    step = RainfallStep()
    assert step.name == "RainfallStep"
    step.execute(test_context)
    assert test_context.world.state.environment["rainfall_intensity"] == 50.0


def test_drainage_step(test_context):
    step = DrainageStep()
    assert step.name == "DrainageStep"
    test_context.active_interventions = [
        {
            "id": "deploy_mobile_pumps",
            "action": "deploy_mobile_pumps",
            "effect": {"drainage_rate_boost": 0.05},
        }
    ]
    step.execute(test_context)
    assert test_context.world.state.environment["drainage_boost"] == pytest.approx(0.05)


def test_metrics_step(test_context):
    step = MetricsStep()
    assert step.name == "MetricsStep"
    test_context.flood_water_levels = {"Z01": 0.6, "Z02": 0.2}
    test_context.casualty_state = {"total_fatalities": 2, "total_injuries": 5}
    test_context.clock.advance()

    step.execute(test_context)
    assert test_context.world.state.metrics["max_water_level"] == pytest.approx(0.6)
    assert test_context.world.state.metrics["avg_water_level"] == pytest.approx(0.4)
    assert test_context.world.state.metrics["total_fatalities"] == 2.0
    assert test_context.world.state.metrics["total_injuries"] == 5.0
    assert any(e["type"] == "SIMULATION_TICK" for e in test_context.world.state.events)


def test_pipeline_execution(test_context):
    pipeline = SimulationPipeline([
        RainfallStep(),
        DrainageStep(),
        MetricsStep(),
    ])
    assert len(pipeline.steps) == 3
    pipeline.execute(test_context)
    assert test_context.world.state.environment["rainfall_intensity"] == 50.0
