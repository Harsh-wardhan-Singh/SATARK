from dataclasses import dataclass, field
from typing import List, Optional

from core.enums import AgentState
from core.types import Position
from twin.entity import Entity

from infrastructure.facility import Facility

from agents.movement import move_toward, reached
from agents.normal_behavior import NormalBehavior
from agents.panic_behavior import PanicBehavior


@dataclass
class HumanAgent(Entity):
    """
    Human agent represented inside the SATARK Digital Twin.

    Human behaviour is deterministic and state-based:

        NORMAL â†’ PANIC â†’ SAFE

    ML is not responsible for controlling this state machine.
    """

    state: AgentState = AgentState.NORMAL

    speed: float = 1.0

    start_position: Optional[Position] = None

    zone_id: Optional[str] = None

    cohort_size: float = 1.0

    evacuation_route: List[str] = field(
        default_factory=list,
        repr=False,
    )

    evacuation_route_positions: List[Position] = field(
        default_factory=list,
        repr=False,
    )

    evacuation_route_index: int = field(
        default=0,
        repr=False,
    )

    target: Optional[Facility] = None

    normal_route: List[Position] = field(default_factory=list)

    normal_behavior: Optional[NormalBehavior] = field(
        default=None,
        repr=False,
    )

    panic_behavior: PanicBehavior = field(
        default_factory=PanicBehavior,
        repr=False,
    )

    def __post_init__(self) -> None:
        if self.speed <= 0:
            raise ValueError("Agent speed must be positive.")

        if self.cohort_size <= 0:
            raise ValueError(
                "Agent cohort_size must be positive."
            )

        if self.zone_id is not None:
            self.zone_id = str(
                self.zone_id
            )

        if self.start_position is None:
            self.start_position = self.position

        if self.normal_route:
            self.normal_behavior = NormalBehavior(
                route=self.normal_route,
                speed=self.speed,
            )

    def set_zone(
        self,
        zone_id: Optional[str],
    ) -> None:
        """
        Set the agent's authoritative zone membership.
        """

        self.zone_id = (
            str(zone_id)
            if zone_id is not None
            else None
        )

    def set_evacuation_route(
        self,
        route: List[str],
        route_positions: Optional[
            List[Position]
        ] = None,
    ) -> None:
        """
        Store the zone-level Dijkstra route and its movement waypoints.
        """

        self.evacuation_route = list(
            route
        )

        self.evacuation_route_positions = (
            list(route_positions)
            if route_positions is not None
            else []
        )

        self.evacuation_route_index = (
            1
            if len(
                self.evacuation_route_positions
            ) > 1
            else 0
        )

    def clear_evacuation_route(
        self,
    ) -> None:
        """
        Clear the current evacuation route.
        """

        self.evacuation_route.clear()
        self.evacuation_route_positions.clear()
        self.evacuation_route_index = 0

    def configure_normal_route(
        self,
        route: List[Position],
    ) -> None:
        """
        Configure the deterministic movement loop used in NORMAL state.
        """
        if not route:
            raise ValueError("Normal route cannot be empty.")

        self.normal_route = route

        self.normal_behavior = NormalBehavior(
            route=route,
            speed=self.speed,
        )

    def enter_panic(
        self,
        safe_centers: List[Facility],
    ) -> bool:
        """
        Transition the agent from NORMAL to PANIC.

        Returns True if a valid safe center was found.
        """
        if self.state == AgentState.SAFE:
            return False

        target = self.panic_behavior.select_safe_center(
            position=self.position,
            facilities=safe_centers,
        )

        if target is None:
            return False

        self.state = AgentState.PANIC
        self.target = target

        self.evacuation_route_index = (
            1
            if len(
                self.evacuation_route_positions
            ) > 1
            else 0
        )

        return True

    def update(
        self,
        delta_time: float,
        safe_centers: Optional[List[Facility]] = None,
    ) -> None:
        """
        Advance the agent by one simulation step.
        """

        if delta_time < 0:
            raise ValueError("delta_time cannot be negative.")

        # ---------------------------------------------------------------------
        # NORMAL
        # ---------------------------------------------------------------------

        if self.state == AgentState.NORMAL:
            if self.normal_behavior is not None:
                self.position = self.normal_behavior.update(
                    position=self.position,
                    delta_time=delta_time,
                )

            return

        # ---------------------------------------------------------------------
        # PANIC
        # ---------------------------------------------------------------------

        if self.state == AgentState.PANIC:
            if self.target is None:
                if safe_centers is None:
                    return

                self.enter_panic(safe_centers)

                if self.target is None:
                    return

            # Follow the zone-level Dijkstra route first.
            if (
                self.evacuation_route_positions
                and self.evacuation_route_index
                < len(
                    self.evacuation_route_positions
                )
            ):
                route_target = (
                    self.evacuation_route_positions[
                        self.evacuation_route_index
                    ]
                )

                self.position = move_toward(
                    current=self.position,
                    target=route_target,
                    speed=self.panic_behavior.speed,
                    delta_time=delta_time,
                )

                if reached(
                    current=self.position,
                    target=route_target,
                    threshold=self.panic_behavior.arrival_threshold,
                ):
                    self.position = route_target
                    self.evacuation_route_index += 1

                return

            # The existing deterministic PanicBehavior remains responsible
            # for the final safe-center movement and SAFE transition.
            self.position = self.panic_behavior.update(
                position=self.position,
                target=self.target,
                delta_time=delta_time,
            )

            if self.panic_behavior.has_reached_target(
                position=self.position,
                target=self.target,
            ):
                self.position = self.target.position
                self.state = AgentState.SAFE

                self.target.add_occupants(
                    max(
                        1,
                        int(
                            round(
                                self.cohort_size
                            )
                        ),
                    )
                )

            return

        # ---------------------------------------------------------------------
        # SAFE
        # ---------------------------------------------------------------------

        if self.state == AgentState.SAFE:
            return

        raise ValueError(
            f"Unsupported agent state: {self.state}"
        )
