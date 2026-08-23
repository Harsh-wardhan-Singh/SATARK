"""
SATARK decision-layer intervention contracts.

This module does not implement intervention logic.
The existing intervention logic remains under
algorithms/intervention/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class Intervention:
    """
    Structured representation of an intervention produced by the
    existing intervention algorithms.

    This object describes an action; it does not execute it.
    """

    intervention_id: str
    name: str
    description: str
    priority: str = "MEDIUM"

    expected_effects: Mapping[str, Any] = field(
        default_factory=dict
    )

    trigger: str | None = None

    source: str = (
        "algorithms.intervention"
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Return a JSON-compatible representation.
        """

        return {
            "intervention_id": self.intervention_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "expected_effects": dict(
                self.expected_effects
            ),
            "trigger": self.trigger,
            "source": self.source,
        }


@dataclass(frozen=True)
class CandidateIntervention:
    """
    Intervention candidate considered by the decision layer.

    This is intentionally separate from Intervention because a
    candidate may be considered without being selected.
    """

    intervention: Intervention

    score: float = 0.0

    rationale: tuple[str, ...] = ()

    applicable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "intervention": (
                self.intervention.to_dict()
            ),
            "score": self.score,
            "rationale": list(
                self.rationale
            ),
            "applicable": self.applicable,
        }