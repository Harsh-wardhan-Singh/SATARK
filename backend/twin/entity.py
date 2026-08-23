from dataclasses import dataclass

from core.types import Position


@dataclass
class Entity:
    """
    Base spatial entity in the SATARK Digital Twin.

    Entity provides the minimum common representation required for
    objects that exist inside the simulated world.
    """

    id: str
    position: Position

    def set_position(self, position: Position) -> None:
        """
        Update the entity's position.
        """
        self.position = position

    def get_position(self) -> Position:
        """
        Return the entity's current position.
        """
        return self.position
