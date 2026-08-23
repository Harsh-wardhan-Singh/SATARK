import random
from typing import Optional

from core.constants import MAX_SIMULATION_TICKS

from simulation.clock import SimulationClock
from simulation.scenario import Scenario
from simulation.world import SimulationWorld


class SimulationEngine:
    """
    Central orchestrator of a SATARK simulation.

    Phase 1 responsibilities:
        - initialize a scenario
        - initialize the Digital Twin
        - control simulation time
        - advance one simulation tick
        - enforce basic simulation limits

    Disaster algorithms, ML, cascade, risk, decision and snapshot
    processing will be integrated in later phases.
    """

    def __init__(
        self,
        scenario: Scenario,
        world: Optional[SimulationWorld] = None,
    ) -> None:
        self.scenario = scenario

        self.world = world or SimulationWorld()

        self.clock = SimulationClock(
            tick_rate=scenario.tick_rate
        )

        self.random = random.Random(
            scenario.random_seed
        )

        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """
        Return whether the simulation has been initialized.
        """
        return self._initialized

    @property
    def is_finished(self) -> bool:
        """
        Return whether the simulation duration has been reached.
        """
        if not self._initialized:
            return False

        return self.clock.has_reached(
            self.scenario.duration
        )

    def initialize(self) -> None:
        """
        Initialize the simulation world from the configured scenario.

        Initialization is intentionally separate from construction so
        creating an engine does not mutate the Digital Twin.
        """
        if self._initialized:
            raise RuntimeError(
                "SimulationEngine is already initialized."
            )

        self.world.initialize(self.scenario)

        self._initialized = True

    def step(self) -> float:
        """
        Advance the simulation by exactly one tick.

        Phase 1 performs only time/state advancement.

        Returns:
            The amount of simulated time advanced.

        Raises:
            RuntimeError: if the simulation is not initialized.
            RuntimeError: if the simulation has already finished.
            RuntimeError: if the maximum tick limit is exceeded.
        """
        self._require_initialized()

        if self.is_finished:
            raise RuntimeError(
                "Simulation has already reached its configured duration."
            )

        if self.clock.current_tick >= MAX_SIMULATION_TICKS:
            raise RuntimeError(
                "Maximum simulation tick limit exceeded."
            )

        delta_time = self.clock.step()

        self.world.advance_time(delta_time)

        self.world.world_state.record_event(
            {
                "type": "SIMULATION_TICK",
                "tick": self.clock.current_tick,
                "simulation_time": self.clock.elapsed_time,
                "delta_time": delta_time,
            }
        )

        return delta_time

    def run_until_complete(self) -> None:
        """
        Advance the simulation until its configured duration is reached.

        Phase 1 only advances time. Later phases will execute the full
        disaster-response pipeline inside step().
        """
        self._require_initialized()

        while not self.is_finished:
            self.step()

    def reset(self) -> None:
        """
        Reset the simulation back to an uninitialized state.
        """
        self.world.reset()
        self.clock.reset()
        self._initialized = False

        # Recreate the deterministic random generator so that
        # rerunning the same scenario with the same seed produces
        # the same random sequence.
        self.random = random.Random(
            self.scenario.random_seed
        )

    def _require_initialized(self) -> None:
        """
        Ensure the engine has been initialized before execution.
        """
        if not self._initialized:
            raise RuntimeError(
                "SimulationEngine has not been initialized."
            )