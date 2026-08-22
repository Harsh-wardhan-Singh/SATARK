import math

from core.types import Position


def distance(
    first: Position,
    second: Position,
) -> float:
    """
    Calculate Euclidean distance between two positions.
    """
    return math.sqrt(
        (second.x - first.x) ** 2
        + (second.y - first.y) ** 2
        + (second.z - first.z) ** 2
    )


def direction(
    start: Position,
    target: Position,
) -> Position:
    """
    Return the normalized direction vector from start to target.

    Returns a zero vector when both positions are identical.
    """
    dx = target.x - start.x
    dy = target.y - start.y
    dz = target.z - start.z

    magnitude = math.sqrt(
        dx ** 2
        + dy ** 2
        + dz ** 2
    )

    if magnitude == 0:
        return Position(0.0, 0.0, 0.0)

    return Position(
        dx / magnitude,
        dy / magnitude,
        dz / magnitude,
    )


def move_toward(
    current: Position,
    target: Position,
    speed: float,
    delta_time: float,
) -> Position:
    """
    Move from current toward target by speed * delta_time.

    The function never moves beyond the target.
    """
    if speed < 0:
        raise ValueError("Speed cannot be negative.")

    if delta_time < 0:
        raise ValueError("delta_time cannot be negative.")

    total_distance = distance(current, target)

    if total_distance == 0:
        return current

    movement_distance = speed * delta_time

    if movement_distance >= total_distance:
        return target

    ratio = movement_distance / total_distance

    return Position(
        x=current.x + (target.x - current.x) * ratio,
        y=current.y + (target.y - current.y) * ratio,
        z=current.z + (target.z - current.z) * ratio,
    )


def reached(
    current: Position,
    target: Position,
    threshold: float = 0.1,
) -> bool:
    """
    Return whether current is sufficiently close to target.
    """
    if threshold < 0:
        raise ValueError("Threshold cannot be negative.")

    return distance(current, target) <= threshold
