from typing import List

from core.enums import AgentState
from core.types import Position

from agents.movement import move_toward


class NormalBehavior:
    """
    Deterministic movement behaviour for a HumanAgent in NORMAL state.
    """

    def __init__(
        self,
        route: List[Position],
        speed: float = 1.0,
    ) -> None:
        if not route:
            raise ValueError("Normal behavior requires a route.")

        if speed <= 0:
            raise ValueError("Normal movement speed must be positive.")

        self.route = route
        self.speed = speed
        self.current_target_index = 0

    @property
    def current_target(self) -> Position:
        """
        Return the current movement target.
        """
        return self.route[self.current_target_index]

    def update(
        self,
        position: Position,
        delta_time: float,
    ) -> Position:
        """
        Move toward the current route target.

        Once a target is reached, advance to the next target.
        The route loops indefinitely.
        """
        new_position = move_toward(
            current=position,
            target=self.current_target,
            speed=self.speed,
            delta_time=delta_time,
        )

        if new_position == self.current_target:
            self.current_target_index = (
                self.current_target_index + 1
            ) % len(self.route)

        return new_position

    def is_applicable(self, state: AgentState) -> bool:
        """
        Return whether this behaviour applies to the supplied agent state.
        """
        return state == AgentState.NORMAL
