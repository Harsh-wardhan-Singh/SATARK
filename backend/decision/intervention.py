"""
SATARK decision-layer intervention contracts.

This module contains structured contracts for interventions produced by
the existing algorithms/intervention implementation.

It does not execute interventions.

Execution remains owned by the simulation layer because applying an
intervention changes the authoritative Digital Twin state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class Intervention:
    """
    Structured representation of an intervention.

    This object describes an action selected or recommended by SATARK.

    It does not execute the action.

    Execution belongs to SimulationEngine so that intervention effects
    remain part of the authoritative simulation state.
    """

    intervention_id: str

    name: str

    description: str

    priority: str = "MEDIUM"

    expected_effects: Mapping[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    trigger: str | None = None

    target: str | None = None

    source: str = (
        "algorithms.intervention"
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Return a JSON-compatible representation.
        """

        return {
            "intervention_id": (
                self.intervention_id
            ),
            "name": self.name,
            "description": (
                self.description
            ),
            "priority": self.priority,
            "expected_effects": dict(
                self.expected_effects
            ),
            "trigger": self.trigger,
            "target": self.target,
            "source": self.source,
        }


@dataclass(frozen=True)
class CandidateIntervention:
    """
    Intervention candidate considered by the decision layer.

    A candidate can exist without being selected or applied.
    """

    intervention: Intervention

    score: float = 0.0

    rationale: tuple[str, ...] = ()

    applicable: bool = True

    def to_dict(self) -> dict[str, Any]:
        """
        Return a JSON-compatible representation.
        """

        return {
            "intervention": (
                self.intervention.to_dict()
            ),
            "score": float(
                self.score
            ),
            "rationale": list(
                self.rationale
            ),
            "applicable": bool(
                self.applicable
            ),
        }