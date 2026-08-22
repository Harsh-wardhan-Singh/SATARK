from dataclasses import dataclass

from core.enums import InfrastructureStatus
from core.types import Position
from twin.entity import Entity


@dataclass
class Building(Entity):
    """
    Building entity inside the SATARK Digital Twin.

    Represents a physical building and its current operational condition.
    """

    status: InfrastructureStatus = InfrastructureStatus.OPERATIONAL

    floors: int = 1

    occupancy: int = 0

    def __post_init__(self) -> None:
        if self.floors <= 0:
            raise ValueError("Building must have at least one floor.")

        if self.occupancy < 0:
            raise ValueError("Building occupancy cannot be negative.")

    @property
    def is_operational(self) -> bool:
        """
        Return whether the building is currently operational.
        """
        return self.status == InfrastructureStatus.OPERATIONAL

    def set_status(self, status: InfrastructureStatus) -> None:
        """
        Update the building's infrastructure status.
        """
        self.status = status

    def set_occupancy(self, occupancy: int) -> None:
        """
        Update the current building occupancy.
        """
        if occupancy < 0:
            raise ValueError("Building occupancy cannot be negative.")

        self.occupancy = occupancy
