"""
SATARK intervention optimization layer.

The optimizer compares baseline and intervention scenarios.

The actual simulation implementation is deliberately injected through
a simulation provider. This prevents the decision layer from creating
a second simulation engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from decision.intervention import (
    CandidateIntervention,
    Intervention,
)


# ----------------------------------------------------------------------
# Simulation result contract
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class SimulationEvaluation:
    """
    Minimal simulation result required by the optimizer.

    This is deliberately independent of SimulationEngine.

    SimulationEngine will later produce the data needed to construct
    this object.
    """

    metrics: Mapping[str, float]

    final_risk_score: float

    casualties: float = 0.0

    infrastructure_damage: float = 0.0

    congestion: float = 0.0

    additional_data: Mapping[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics": dict(
                self.metrics
            ),
            "final_risk_score": (
                self.final_risk_score
            ),
            "casualties": self.casualties,
            "infrastructure_damage": (
                self.infrastructure_damage
            ),
            "congestion": self.congestion,
            "additional_data": dict(
                self.additional_data
            ),
        }


# ----------------------------------------------------------------------
# Candidate comparison
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class OptimizationCandidateResult:
    """
    Result of evaluating one intervention candidate against baseline.
    """

    intervention: Intervention

    baseline: SimulationEvaluation

    intervention_result: SimulationEvaluation

    improvement_score: float

    risk_reduction: float

    casualty_reduction: float

    infrastructure_improvement: float

    congestion_improvement: float

    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "intervention": (
                self.intervention.to_dict()
            ),
            "baseline": (
                self.baseline.to_dict()
            ),
            "intervention_result": (
                self.intervention_result.to_dict()
            ),
            "improvement_score": (
                self.improvement_score
            ),
            "risk_reduction": (
                self.risk_reduction
            ),
            "casualty_reduction": (
                self.casualty_reduction
            ),
            "infrastructure_improvement": (
                self.infrastructure_improvement
            ),
            "congestion_improvement": (
                self.congestion_improvement
            ),
            "rationale": self.rationale,
        }


# ----------------------------------------------------------------------
# Final optimization result
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class OptimizationResult:
    """
    Complete optimization result.

    Contains every evaluated candidate and the selected best option.
    """

    baseline: SimulationEvaluation

    candidates: tuple[
        OptimizationCandidateResult,
        ...
    ]

    selected_intervention: Intervention | None

    selection_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline": (
                self.baseline.to_dict()
            ),
            "candidates": [
                candidate.to_dict()
                for candidate in self.candidates
            ],
            "selected_intervention": (
                self.selected_intervention.to_dict()
                if self.selected_intervention
                else None
            ),
            "selection_reason": (
                self.selection_reason
            ),
        }


# ----------------------------------------------------------------------
# Simulation provider
# ----------------------------------------------------------------------


SimulationProvider = Callable[
    [
        Mapping[str, Any] | None,
    ],
    SimulationEvaluation,
]


# ----------------------------------------------------------------------
# Optimization engine
# ----------------------------------------------------------------------


class OptimizationEngine:
    """
    Compares candidate interventions using actual simulation results.

    The simulation provider is injected.

    This is intentional:

        OptimizationEngine
                ↓
        SimulationProvider
                ↓
        actual SimulationEngine

    The optimizer therefore never implements disaster simulation.
    """

    def __init__(
        self,
        simulation_provider: SimulationProvider | None = None,
    ) -> None:

        self.simulation_provider = (
            simulation_provider
        )

    # ------------------------------------------------------------------
    # Main API
    # ------------------------------------------------------------------

    def optimize(
        self,
        *,
        baseline_scenario: Mapping[
            str,
            Any,
        ],
        candidates: Sequence[
            CandidateIntervention
        ],
    ) -> OptimizationResult:
        """
        Evaluate candidate interventions against a baseline.

        Raises:
            RuntimeError if no simulation provider has been configured.
        """

        self._require_simulation_provider()

        baseline = (
            self.simulation_provider(
                None
            )
        )

        evaluated: list[
            OptimizationCandidateResult
        ] = []

        for candidate in candidates:
            if not candidate.applicable:
                continue

            intervention_result = (
                self.simulation_provider(
                    self._build_intervention_scenario(
                        baseline_scenario,
                        candidate.intervention,
                    )
                )
            )

            result = (
                self._compare_candidate(
                    candidate.intervention,
                    baseline,
                    intervention_result,
                )
            )

            evaluated.append(
                result
            )

        evaluated.sort(
            key=lambda result: (
                result.improvement_score
            ),
            reverse=True,
        )

        if evaluated:
            selected = evaluated[0]

            return OptimizationResult(
                baseline=baseline,
                candidates=tuple(
                    evaluated
                ),
                selected_intervention=(
                    selected.intervention
                ),
                selection_reason=(
                    selected.rationale
                ),
            )

        return OptimizationResult(
            baseline=baseline,
            candidates=(),
            selected_intervention=None,
            selection_reason=(
                "No applicable intervention "
                "candidates were available."
            ),
        )

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    @staticmethod
    def _compare_candidate(
        intervention: Intervention,
        baseline: SimulationEvaluation,
        intervention_result: SimulationEvaluation,
    ) -> OptimizationCandidateResult:
        """
        Compare baseline and intervention outcomes.

        Lower is better for:
            risk
            casualties
            infrastructure damage
            congestion

        Therefore improvement is calculated as reduction.
        """

        risk_reduction = (
            baseline.final_risk_score
            - intervention_result.final_risk_score
        )

        casualty_reduction = (
            baseline.casualties
            - intervention_result.casualties
        )

        infrastructure_improvement = (
            baseline.infrastructure_damage
            - intervention_result.infrastructure_damage
        )

        congestion_improvement = (
            baseline.congestion
            - intervention_result.congestion
        )

        # Weighted objective.
        #
        # Risk receives the highest weight because it is the primary
        # decision-level outcome.
        improvement_score = (
            risk_reduction * 0.50
            +
            casualty_reduction * 0.25
            +
            infrastructure_improvement * 0.15
            +
            congestion_improvement * 0.10
        )

        if improvement_score > 0:
            rationale = (
                f"{intervention.name} produced the strongest "
                f"simulated improvement with a composite "
                f"improvement score of "
                f"{improvement_score:.2f}."
            )

        elif improvement_score == 0:
            rationale = (
                f"{intervention.name} produced no measurable "
                "improvement over the baseline simulation."
            )

        else:
            rationale = (
                f"{intervention.name} performed worse than "
                "the baseline simulation."
            )

        return OptimizationCandidateResult(
            intervention=intervention,
            baseline=baseline,
            intervention_result=(
                intervention_result
            ),
            improvement_score=(
                improvement_score
            ),
            risk_reduction=risk_reduction,
            casualty_reduction=(
                casualty_reduction
            ),
            infrastructure_improvement=(
                infrastructure_improvement
            ),
            congestion_improvement=(
                congestion_improvement
            ),
            rationale=rationale,
        )

    # ------------------------------------------------------------------
    # Scenario construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_intervention_scenario(
        baseline_scenario: Mapping[
            str,
            Any,
        ],
        intervention: Intervention,
    ) -> dict[str, Any]:
        """
        Create a candidate scenario without mutating the baseline.

        The actual SimulationEngine will interpret this scenario later.
        """

        scenario = dict(
            baseline_scenario
        )

        scenario[
            "intervention"
        ] = intervention.to_dict()

        return scenario

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _require_simulation_provider(
        self,
    ) -> None:
        if self.simulation_provider is None:
            raise RuntimeError(
                "OptimizationEngine requires a simulation "
                "provider. Connect it to SimulationEngine "
                "before running optimization."
            )