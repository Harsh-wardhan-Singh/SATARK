def test_simulation_placeholder():
    assert True

import pytest

from core.enums import CalamityType
from core.types import Position, SimulationConfig
from twin.entity import Entity

from simulation.clock import SimulationClock
from simulation.engine import SimulationEngine
from simulation.scenario import Scenario
from simulation.world import SimulationWorld


def create_test_scenario(
    duration: float = 1.0,
    tick_rate: float = 10.0,
    random_seed: int = 42,
) -> Scenario:
    """
    Create a minimal deterministic scenario for testing.
    """
    config = SimulationConfig(
        duration=duration,
        tick_rate=tick_rate,
        calamity_type=CalamityType.FLOOD,
        random_seed=random_seed,
    )

    entity = Entity(
        id="test-agent",
        position=Position(
            x=0.0,
            y=0.0,
            z=0.0,
        ),
    )

    return Scenario(
        config=config,
        initial_entities=(entity,),
        initial_environment={
            "test_value": 1.0,
        },
    )


def test_clock_delta_time():
    """
    A 10 Hz clock must advance by 0.1 seconds per tick.
    """
    clock = SimulationClock(tick_rate=10.0)

    assert clock.delta_time == pytest.approx(0.1)

    delta_time = clock.step()

    assert delta_time == pytest.approx(0.1)
    assert clock.current_tick == 1
    assert clock.elapsed_time == pytest.approx(0.1)


def test_clock_reset():
    """
    Resetting the clock must return it to its initial state.
    """
    clock = SimulationClock(tick_rate=10.0)

    clock.step()
    clock.step()

    clock.reset()

    assert clock.current_tick == 0
    assert clock.elapsed_time == pytest.approx(0.0)


def test_scenario_initialization():
    """
    Scenario must preserve its configuration and initial state.
    """
    scenario = create_test_scenario()

    assert scenario.calamity_type == CalamityType.FLOOD
    assert scenario.duration == pytest.approx(1.0)
    assert scenario.tick_rate == pytest.approx(10.0)
    assert scenario.random_seed == 42

    assert len(scenario.get_initial_entities()) == 1
    assert scenario.get_initial_environment()["test_value"] == 1.0


def test_simulation_world_uses_digital_twin():
    """
    SimulationWorld must expose the authoritative Digital Twin state
    rather than maintaining a competing state object.
    """
    scenario = create_test_scenario()

    world = SimulationWorld()
    twin = world.initialize(scenario)

    assert world.twin is twin
    assert world.world_state is twin.world_state

    assert world.world_state.current_tick == 0
    assert world.world_state.simulation_time == pytest.approx(0.0)

    assert world.world_state.active_calamity == CalamityType.FLOOD

    assert "test-agent" in world.world_state.entities
    assert world.world_state.environment["test_value"] == 1.0


def test_engine_initialization():
    """
    Engine initialization must create the Digital Twin state but must
    not advance simulation time.
    """
    scenario = create_test_scenario()

    engine = SimulationEngine(scenario)

    assert not engine.is_initialized

    engine.initialize()

    assert engine.is_initialized

    assert engine.world.world_state.current_tick == 0
    assert engine.world.world_state.simulation_time == pytest.approx(0.0)


def test_engine_single_step():
    """
    A single engine step must advance both the clock and authoritative
    WorldState by the same delta time.
    """
    scenario = create_test_scenario()

    engine = SimulationEngine(scenario)
    engine.initialize()

    delta_time = engine.step()

    assert delta_time == pytest.approx(0.1)

    assert engine.clock.current_tick == 1
    assert engine.clock.elapsed_time == pytest.approx(0.1)

    assert engine.world.world_state.current_tick == 1
    assert engine.world.world_state.simulation_time == pytest.approx(0.1)


def test_engine_runs_until_duration():
    """
    Engine must stop once the configured duration is reached.
    """
    scenario = create_test_scenario(
        duration=0.5,
        tick_rate=10.0,
    )

    engine = SimulationEngine(scenario)
    engine.initialize()

    engine.run_until_complete()

    assert engine.is_finished
    assert engine.clock.current_tick == 5
    assert engine.clock.elapsed_time == pytest.approx(0.5)

    assert engine.world.world_state.current_tick == 5
    assert engine.world.world_state.simulation_time == pytest.approx(0.5)


def test_engine_cannot_step_after_completion():
    """
    Once the configured duration has been reached, another step must
    not be allowed.
    """
    scenario = create_test_scenario(
        duration=0.1,
        tick_rate=10.0,
    )

    engine = SimulationEngine(scenario)
    engine.initialize()

    engine.step()

    assert engine.is_finished

    with pytest.raises(RuntimeError):
        engine.step()


def test_engine_requires_initialization():
    """
    The engine must not execute before initialization.
    """
    scenario = create_test_scenario()

    engine = SimulationEngine(scenario)

    with pytest.raises(RuntimeError):
        engine.step()


def test_engine_reset():
    """
    Reset must return the engine to its initial uninitialized state.
    """
    scenario = create_test_scenario()

    engine = SimulationEngine(scenario)
    engine.initialize()
    engine.step()

    engine.reset()

    assert not engine.is_initialized
    assert engine.clock.current_tick == 0
    assert engine.clock.elapsed_time == pytest.approx(0.0)

    assert engine.world.twin is not None
    assert engine.world.world_state.current_tick == 0
    assert engine.world.world_state.simulation_time == pytest.approx(0.0)