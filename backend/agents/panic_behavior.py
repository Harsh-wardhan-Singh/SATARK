from typing import Iterable, Optional

from core.enums import AgentState
from core.types import Position

from infrastructure.facility import Facility
from agents.movement import distance, move_toward, reached


class PanicBehavior:
    """
    Deterministic evacuation behaviour for a HumanAgent in PANIC state.

    The behaviour selects the nearest available safe center and moves the
    agent toward it.
    """

    def __init__(
        self,
        speed: float = 2.0,
        arrival_threshold: float = 0.5,
    ) -> None:
        if speed <= 0:
            raise ValueError("Panic movement speed must be positive.")

        if arrival_threshold < 0:
            raise ValueError(
                "Arrival threshold cannot be negative."
            )

        self.speed = speed
        self.arrival_threshold = arrival_threshold

    def select_safe_center(
        self,
        position: Position,
        facilities: Iterable[Facility],
    ) -> Optional[Facility]:
        """
        Select the nearest operational safe center with available capacity.
        """
        candidates = [
            facility
            for facility in facilities
            if facility.is_safe_center
            and facility.is_operational
            and facility.available_capacity > 0
        ]

        if not candidates:
            return None

        return min(
            candidates,
            key=lambda facility: distance(
                position,
                facility.position,
            ),
        )

    def update(
        self,
        position: Position,
        target: Facility,
        delta_time: float,
    ) -> Position:
        """
        Move the agent toward its selected safe center.
        """
        return move_toward(
            current=position,
            target=target.position,
            speed=self.speed,
            delta_time=delta_time,
        )

    def has_reached_target(
        self,
        position: Position,
        target: Facility,
    ) -> bool:
        """
        Determine whether the agent has reached the safe center.
        """
        return reached(
            current=position,
            target=target.position,
            threshold=self.arrival_threshold,
        )

    def is_applicable(self, state: AgentState) -> bool:
        """
        Return whether this behaviour applies to the supplied state.
        """
        return state == AgentState.PANIC
