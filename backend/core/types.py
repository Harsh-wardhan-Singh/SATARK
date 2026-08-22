from dataclasses import dataclass, field
from typing import Optional

from core.enums import CalamityType


@dataclass(frozen=True)
class Position:
    """
    Spatial position of an entity in the SATARK simulation world.

    Coordinates are represented using the simulation's logical coordinate
    system. The 3D frontend may later transform these coordinates into
    Three.js coordinates.
    """

    x: float
    y: float
    z: float = 0.0


@dataclass
class SimulationConfig:
    """
    Configuration required to execute a SATARK simulation.

    This describes simulation parameters, not simulation state.
    """

    duration: float
    tick_rate: float
    calamity_type: CalamityType

    random_seed: Optional[int] = None

    def __post_init__(self) -> None:
        if self.duration <= 0:
            raise ValueError("Simulation duration must be greater than 0.")

        if self.tick_rate <= 0:
            raise ValueError("Simulation tick rate must be greater than 0.")
