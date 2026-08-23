"""
SATARK decision response layer.

This module describes how a selected intervention should be presented
to the simulation/control layer.

It does not execute the intervention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from decision.intervention import (
    Intervention,
)


@dataclass(frozen=True)
class Response:
    """
    Structured response generated from an intervention.

    The simulation layer may later use this object to apply the action.
    """

    intervention: Intervention

    priority: str

    reason: str

    target: str | None = None

    execution_parameters: Mapping[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Return a JSON-compatible representation.
        """

        return {
            "intervention": (
                self.intervention.to_dict()
            ),
            "priority": self.priority,
            "reason": self.reason,
            "target": self.target,
            "execution_parameters": dict(
                self.execution_parameters
            ),
        }


class ResponseEngine:
    """
    Builds structured responses from interventions.

    This class does not execute them.
    """

    def build_response(
        self,
        intervention: Intervention,
        *,
        reason: str,
        target: str | None = None,
        execution_parameters: Mapping[
            str,
            Any,
        ] | None = None,
    ) -> Response:
        """
        Build a response for a selected intervention.
        """

        return Response(
            intervention=intervention,
            priority=(
                intervention.priority
            ),
            reason=reason,
            target=target,
            execution_parameters=(
                dict(
                    execution_parameters
                    or {}
                )
            ),
        )