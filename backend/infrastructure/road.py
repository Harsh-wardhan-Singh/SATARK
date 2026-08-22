from dataclasses import dataclass

from core.enums import InfrastructureStatus
from core.types import Position
from twin.entity import Entity


@dataclass
class Road(Entity):
    """
    Road entity inside the SATARK Digital Twin.

    A Road represents a traversable transportation link whose operational
    state can change during a disaster.
    """

    status: InfrastructureStatus = InfrastructureStatus.OPERATIONAL

    capacity: float = 100.0

    length: float = 1.0

    def __post_init__(self) -> None:
        if self.capacity < 0:
            raise ValueError("Road capacity cannot be negative.")

        if self.length <= 0:
            raise ValueError("Road length must be greater than 0.")

    @property
    def is_operational(self) -> bool:
        """
        Return whether the road can currently be used.
        """
        return self.status == InfrastructureStatus.OPERATIONAL

    @property
    def is_blocked(self) -> bool:
        """
        Return whether the road is currently blocked.
        """
        return self.status == InfrastructureStatus.BLOCKED

    def set_status(self, status: InfrastructureStatus) -> None:
        """
        Update the operational status of the road.
        """
        self.status = status
