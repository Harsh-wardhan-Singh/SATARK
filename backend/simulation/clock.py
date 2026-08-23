from dataclasses import dataclass

from core.constants import DEFAULT_TICK_RATE


@dataclass
class SimulationClock:
    """
    Controls deterministic simulation time.

    SimulationClock is responsible for determining the duration of each
    simulation tick. It does not modify WorldState directly.

    WorldState remains responsible for storing the authoritative
    simulation time and tick count.
    """

    tick_rate: float = DEFAULT_TICK_RATE

    current_tick: int = 0
    elapsed_time: float = 0.0

    def __post_init__(self) -> None:
        if self.tick_rate <= 0:
            raise ValueError(
                "Simulation tick rate must be greater than 0."
            )

    @property
    def delta_time(self) -> float:
        """
        Return the fixed amount of simulated time represented by one tick.

        Example:
            tick_rate = 10
            delta_time = 0.1 seconds
        """
        return 1.0 / self.tick_rate

    def step(self) -> float:
        """
        Advance the simulation clock by exactly one tick.

        Returns:
            The amount of simulated time advanced.
        """
        delta_time = self.delta_time

        self.current_tick += 1
        self.elapsed_time += delta_time

        return delta_time

    def reset(self) -> None:
        """
        Reset the clock to its initial state.
        """
        self.current_tick = 0
        self.elapsed_time = 0.0

    def has_reached(self, duration: float) -> bool:
        """
        Return whether the requested simulation duration has been reached.
        """
        if duration <= 0:
            raise ValueError(
                "Simulation duration must be greater than 0."
            )

        return self.elapsed_time >= duration