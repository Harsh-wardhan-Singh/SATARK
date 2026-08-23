"""
SATARK decision priority engine.

This layer consumes the existing risk-assessment algorithm output.

It does not calculate risk itself and does not execute interventions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class PriorityItem:
    """
    One prioritized risk factor.
    """

    factor: str

    score: float

    priority: str

    rationale: str

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Return a JSON-compatible representation.
        """

        return {
            "factor": self.factor,
            "score": float(
                self.score
            ),
            "priority": self.priority,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class PriorityResult:
    """
    Ordered decision priorities.
    """

    overall_priority: str

    items: tuple[
        PriorityItem,
        ...,
    ]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Return a JSON-compatible representation.
        """

        return {
            "overall_priority": (
                self.overall_priority
            ),
            "items": [
                item.to_dict()
                for item in self.items
            ],
        }


class PriorityEngine:
    """
    Converts an existing risk report into decision priorities.

    The risk report is produced by the authoritative RiskEngine.

    No risk formula is duplicated here.
    """

    PRIORITY_THRESHOLDS = {
        "CRITICAL": 75.0,
        "HIGH": 50.0,
        "MEDIUM": 25.0,
    }

    def evaluate(
        self,
        risk_assessment: Mapping[
            str,
            Any,
        ],
    ) -> PriorityResult:
        """
        Evaluate decision priorities from an existing risk assessment.

        Expected input:

            {
                "composite_risk_score": ...,
                "breakdown": {
                    "casualties": ...,
                    "infrastructure_failure": ...,
                    "flooding_severity": ...,
                    "crowd_congestion": ...
                }
            }
        """

        composite_score = (
            self._extract_composite_score(
                risk_assessment
            )
        )

        breakdown = (
            self._extract_breakdown(
                risk_assessment
            )
        )

        items: list[
            PriorityItem
        ] = []

        for factor, score in (
            breakdown.items()
        ):

            numeric_score = float(
                score
            )

            items.append(
                PriorityItem(
                    factor=str(
                        factor
                    ),
                    score=numeric_score,
                    priority=(
                        self._priority_from_score(
                            numeric_score
                        )
                    ),
                    rationale=(
                        self._build_rationale(
                            factor=str(
                                factor
                            ),
                            score=numeric_score,
                        )
                    ),
                )
            )

        items.sort(
            key=lambda item: (
                item.score
            ),
            reverse=True,
        )

        return PriorityResult(
            overall_priority=(
                self._priority_from_score(
                    composite_score
                )
            ),
            items=tuple(
                items
            ),
        )

    # ------------------------------------------------------------------
    # Input extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_composite_score(
        risk_assessment: Mapping[
            str,
            Any,
        ],
    ) -> float:
        """
        Extract the overall risk score.
        """

        for key in (
            "composite_risk_score",
            "composite_score",
            "risk_score",
        ):

            if key in risk_assessment:
                return float(
                    risk_assessment[key]
                )

        raise ValueError(
            "Risk assessment does not contain "
            "a composite risk score."
        )

    @staticmethod
    def _extract_breakdown(
        risk_assessment: Mapping[
            str,
            Any,
        ],
    ) -> Mapping[
        str,
        Any,
    ]:
        """
        Extract the risk-component breakdown.
        """

        breakdown = (
            risk_assessment.get(
                "breakdown"
            )
        )

        if breakdown is None:
            breakdown = (
                risk_assessment.get(
                    "risk_breakdown"
                )
            )

        if not isinstance(
            breakdown,
            Mapping,
        ):
            raise ValueError(
                "Risk assessment does not contain "
                "a valid risk breakdown."
            )

        return breakdown

    # ------------------------------------------------------------------
    # Priority logic
    # ------------------------------------------------------------------

    @classmethod
    def _priority_from_score(
        cls,
        score: float,
    ) -> str:

        if score >= cls.PRIORITY_THRESHOLDS[
            "CRITICAL"
        ]:
            return "CRITICAL"

        if score >= cls.PRIORITY_THRESHOLDS[
            "HIGH"
        ]:
            return "HIGH"

        if score >= cls.PRIORITY_THRESHOLDS[
            "MEDIUM"
        ]:
            return "MEDIUM"

        return "LOW"

    @staticmethod
    def _build_rationale(
        *,
        factor: str,
        score: float,
    ) -> str:

        if score >= 75:
            return (
                f"{factor} is at a critical level "
                "and requires immediate attention."
            )

        if score >= 50:
            return (
                f"{factor} represents a high-priority "
                "risk driver."
            )

        if score >= 25:
            return (
                f"{factor} represents a moderate "
                "risk driver."
            )

        return (
            f"{factor} is currently a lower-priority "
            "risk driver."
        )