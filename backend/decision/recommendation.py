"""
SATARK decision recommendation layer.

The actual intervention-selection rules remain in:

    algorithms/intervention/recommendations.py

This module converts those existing algorithm outputs into structured
decision-layer objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from decision.intervention import (
    Intervention,
)
from decision.priority import (
    PriorityEngine,
    PriorityResult,
)
from decision.response import (
    Response,
    ResponseEngine,
)


@dataclass(frozen=True)
class Recommendation:
    """
    Final explainable decision recommendation.
    """

    intervention: Intervention

    priority: str

    reason: str

    response: Response

    source: str = (
        "algorithms.intervention.recommendations"
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
            "response": (
                self.response.to_dict()
            ),
            "source": self.source,
        }


class RecommendationEngine:
    """
    Adapter around the existing intervention recommendation algorithm.

    It does not duplicate intervention-selection thresholds.
    """

    def __init__(
        self,
        priority_engine: PriorityEngine | None = None,
        response_engine: ResponseEngine | None = None,
    ) -> None:

        self.priority_engine = (
            priority_engine
            if priority_engine is not None
            else PriorityEngine()
        )

        self.response_engine = (
            response_engine
            if response_engine is not None
            else ResponseEngine()
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def recommend(
        self,
        *,
        risk_assessment: Mapping[
            str,
            Any,
        ],
        algorithm_recommendations: Sequence[
            Mapping[str, Any]
        ],
    ) -> list[Recommendation]:
        """
        Convert existing algorithm recommendations into structured
        decision recommendations.

        `algorithm_recommendations` must come from:

            algorithms/intervention/recommendations.py

        No intervention thresholds are calculated here.
        """

        priorities = (
            self.priority_engine.evaluate(
                risk_assessment
            )
        )

        priority_map = {
            item.factor: item
            for item in priorities.items
        }

        recommendations: list[
            Recommendation
        ] = []

        for raw in (
            algorithm_recommendations
        ):

            intervention = (
                self._convert_algorithm_intervention(
                    raw=raw,
                    priority_map=(
                        priority_map
                    ),
                    priorities=priorities,
                )
            )

            reason = (
                self._extract_reason(
                    raw
                )
            )

            response = (
                self.response_engine
                .build_response(
                    intervention,
                    reason=reason,
                    target=(
                        self._extract_target(
                            raw
                        )
                    ),
                    execution_parameters=(
                        self._extract_execution_parameters(
                            raw
                        )
                    ),
                )
            )

            recommendations.append(
                Recommendation(
                    intervention=(
                        intervention
                    ),
                    priority=(
                        intervention.priority
                    ),
                    reason=reason,
                    response=response,
                )
            )

        recommendations.sort(
            key=self._recommendation_sort_key
        )

        return recommendations

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def _convert_algorithm_intervention(
        self,
        raw: Mapping[
            str,
            Any,
        ],
        priority_map: Mapping[
            str,
            Any,
        ],
        priorities: PriorityResult,
    ) -> Intervention:
        """
        Convert an existing algorithm intervention into the SATARK
        decision-layer Intervention contract.
        """

        intervention_id = (
            raw.get("id")
            or raw.get("intervention_id")
            or raw.get("action")
        )

        if not intervention_id:
            raise ValueError(
                "Algorithm intervention is missing "
                "an intervention identifier."
            )

        name = (
            raw.get("name")
            or raw.get("title")
            or str(
                intervention_id
            )
        )

        description = (
            raw.get("description")
            or raw.get("reason")
            or ""
        )

        priority = (
            self._determine_intervention_priority(
                raw=raw,
                priority_map=(
                    priority_map
                ),
                priorities=priorities,
            )
        )

        effects = (
            raw.get("effects")
            or raw.get("expected_effects")
            or {}
        )

        trigger = raw.get(
            "trigger"
        )

        target = raw.get(
            "target"
        )

        return Intervention(
            intervention_id=str(
                intervention_id
            ),
            name=str(
                name
            ),
            description=str(
                description
            ),
            priority=priority,
            expected_effects=(
                effects
            ),
            trigger=(
                str(trigger)
                if trigger is not None
                else None
            ),
            target=(
                str(target)
                if target is not None
                else None
            ),
        )

    @staticmethod
    def _determine_intervention_priority(
        *,
        raw: Mapping[
            str,
            Any,
        ],
        priority_map: Mapping[
            str,
            Any,
        ],
        priorities: PriorityResult,
    ) -> str:
        """
        Prefer explicit priority from the existing algorithm.

        Otherwise derive priority from the associated risk factor.

        Otherwise use the overall risk priority.
        """

        explicit_priority = raw.get(
            "priority"
        )

        if explicit_priority:
            return str(
                explicit_priority
            ).upper()

        relevant_factor = (
            raw.get("risk_factor")
            or raw.get("factor")
        )

        if (
            relevant_factor
            in priority_map
        ):
            return (
                priority_map[
                    relevant_factor
                ].priority
            )

        return (
            priorities.overall_priority
        )

    @staticmethod
    def _extract_reason(
        raw: Mapping[
            str,
            Any,
        ],
    ) -> str:

        return str(
            raw.get(
                "reason",
                raw.get(
                    "description",
                    "Intervention recommended "
                    "by the existing algorithm.",
                ),
            )
        )

    @staticmethod
    def _extract_target(
        raw: Mapping[
            str,
            Any,
        ],
    ) -> str | None:

        target = raw.get(
            "target"
        )

        if target is None:
            return None

        return str(
            target
        )

    @staticmethod
    def _extract_execution_parameters(
        raw: Mapping[
            str,
            Any,
        ],
    ) -> Mapping[
        str,
        Any,
    ]:

        parameters = raw.get(
            "execution_parameters"
        )

        if parameters is None:
            parameters = raw.get(
                "parameters"
            )

        if not isinstance(
            parameters,
            Mapping,
        ):
            return {}

        return dict(
            parameters
        )

    @staticmethod
    def _recommendation_sort_key(
        recommendation: Recommendation,
    ) -> tuple[
        int,
        str,
    ]:

        priority_order = {
            "CRITICAL": 0,
            "HIGH": 1,
            "MEDIUM": 2,
            "LOW": 3,
        }

        return (
            priority_order.get(
                recommendation.priority,
                4,
            ),
            recommendation.intervention.intervention_id,
        )