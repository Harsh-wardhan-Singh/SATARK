from __future__ import annotations

from dataclasses import dataclass

from core.constants import MAX_SIMULATION_TICKS


@dataclass
class SimulationClock:
    """
    Controls deterministic simulation time progression.

    The clock only manages time.
    It does not execute simulation logic.
    """

    tick_rate: float

    current_tick: int = 0
    simulation_time: float = 0.0

    def __post_init__(self) -> None:
        if self.tick_rate <= 0:
            raise ValueError(
                "Simulation tick rate must be greater than 0."
            )

    @property
    def delta_time(self) -> float:
        """
        Amount of simulation time represented by one tick.
        """
        return 1.0 / self.tick_rate

    def advance(self) -> float:
        """
        Advance the simulation by one tick.

        Returns:
            The delta time for the tick.
        """

        if self.current_tick >= MAX_SIMULATION_TICKS:
            raise RuntimeError(
                "Maximum simulation tick limit reached."
            )

        self.current_tick += 1
        self.simulation_time += self.delta_time

        return self.delta_time

    def reset(self) -> None:
        """
        Reset the clock.
        """

        self.current_tick = 0
        self.simulation_time = 0.0