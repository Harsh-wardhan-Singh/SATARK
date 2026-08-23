from typing import Iterable, Optional

from twin.entity import Entity
from twin.state import WorldState
from twin.twin import DigitalTwin


class TwinManager:
    """
    Manages the lifecycle of SATARK Digital Twin instances.

    The manager does not contain simulation logic. It is responsible only
    for creating, initializing, accessing, and resetting the Digital Twin.
    """

    def __init__(self) -> None:
        self._active_twin: Optional[DigitalTwin] = None

    def create_twin(
        self,
        world_state: Optional[WorldState] = None,
    ) -> DigitalTwin:
        """
        Create and register a new active Digital Twin.
        """
        self._active_twin = DigitalTwin(world_state)
        return self._active_twin

    def initialize_twin(
        self,
        entities: Optional[Iterable[Entity]] = None,
        world_state: Optional[WorldState] = None,
    ) -> DigitalTwin:
        """
        Create a Digital Twin and optionally populate it with entities.
        """
        twin = self.create_twin(world_state)

        if entities is not None:
            twin.add_entities(entities)

        return twin

    def get_active_twin(self) -> DigitalTwin:
        """
        Return the currently active Digital Twin.
        """
        if self._active_twin is None:
            raise RuntimeError("No active Digital Twin exists.")

        return self._active_twin

    def reset_twin(self) -> DigitalTwin:
        """
        Reset the active Digital Twin to an empty world.

        If no active Digital Twin exists, a new one is created.
        """
        if self._active_twin is None:
            return self.create_twin()

        self._active_twin.reset()
        return self._active_twin

    def replace_twin(
        self,
        world_state: WorldState,
    ) -> DigitalTwin:
        """
        Replace the active Digital Twin with a new world state.
        """
        self._active_twin = DigitalTwin(world_state)
        return self._active_twin
