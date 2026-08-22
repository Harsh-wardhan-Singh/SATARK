from dataclasses import dataclass

from core.enums import InfrastructureStatus
from core.types import Position
from twin.entity import Entity


@dataclass
class Facility(Entity):
    """
    Facility entity inside the SATARK Digital Twin.

    A facility may represent hospitals, shelters, emergency facilities,
    safe centers, or other operational locations.
    """

    facility_type: str = "GENERAL"

    status: InfrastructureStatus = InfrastructureStatus.OPERATIONAL

    capacity: int = 0

    current_occupancy: int = 0

    def __post_init__(self) -> None:
        if self.capacity < 0:
            raise ValueError("Facility capacity cannot be negative.")

        if self.current_occupancy < 0:
            raise ValueError(
                "Facility current occupancy cannot be negative."
            )

        if self.current_occupancy > self.capacity:
            raise ValueError(
                "Facility occupancy cannot exceed facility capacity."
            )

    @property
    def is_operational(self) -> bool:
        """
        Return whether the facility is currently operational.
        """
        return self.status == InfrastructureStatus.OPERATIONAL

    @property
    def is_safe_center(self) -> bool:
        """
        Return whether this facility functions as a safe center.
        """
        return self.facility_type.upper() == "SAFE_CENTER"

    @property
    def available_capacity(self) -> int:
        """
        Return the currently available capacity.
        """
        return self.capacity - self.current_occupancy

    def set_status(self, status: InfrastructureStatus) -> None:
        """
        Update the facility's infrastructure status.
        """
        self.status = status

    def add_occupants(self, count: int) -> None:
        """
        Add people to the facility.
        """
        if count < 0:
            raise ValueError("Occupant count cannot be negative.")

        if self.current_occupancy + count > self.capacity:
            raise ValueError(
                "Facility capacity exceeded."
            )

        self.current_occupancy += count

    def remove_occupants(self, count: int) -> None:
        """
        Remove people from the facility.
        """
        if count < 0:
            raise ValueError("Occupant count cannot be negative.")

        if count > self.current_occupancy:
            raise ValueError(
                "Cannot remove more occupants than currently present."
            )

        self.current_occupancy -= count
