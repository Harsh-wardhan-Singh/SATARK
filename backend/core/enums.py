from enum import Enum


class AgentState(str, Enum):
    """
    State of a human agent inside the simulation.
    """

    NORMAL = "NORMAL"
    PANIC = "PANIC"
    SAFE = "SAFE"


class CalamityType(str, Enum):
    """
    Supported calamity types.
    """

    FLOOD = "FLOOD"
    # TSUNAMI = "TSUNAMI"
    EARTHQUAKE = "EARTHQUAKE"


class InfrastructureStatus(str, Enum):
    """
    Operational state of infrastructure entities.
    """

    OPERATIONAL = "OPERATIONAL"
    DAMAGED = "DAMAGED"
    BLOCKED = "BLOCKED"
    DESTROYED = "DESTROYED"


class SeverityLevel(str, Enum):
    """
    General severity classification used across SATARK.
    """

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"