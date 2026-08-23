"""
SATARK intervention optimization layer.

The optimizer compares a baseline simulation against candidate
intervention simulations.

The optimizer does not implement disaster simulation.

Instead:

    OptimizationEngine
            ↓
    SimulationProvider
            ↓
    actual SimulationEngine

This keeps optimization independent from simulation mechanics.
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

    This object is deliberately independent of SimulationEngine.

    SimulationEngine produces this data after a complete simulation.
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

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Return a JSON-compatible representation.
        """

        return {
            "metrics": {
                key: float(value)
                for key, value
                in self.metrics.items()
            },
            "final_risk_score": float(
                self.final_risk_score
            ),
            "casualties": float(
                self.casualties
            ),
            "infrastructure_damage": float(
                self.infrastructure_damage
            ),
            "congestion": float(
                self.congestion
            ),
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
            "baseline": (
                self.baseline.to_dict()
            ),
            "intervention_result": (
                self.intervention_result.to_dict()
            ),
            "improvement_score": float(
                self.improvement_score
            ),
            "risk_reduction": float(
                self.risk_reduction
            ),
            "casualty_reduction": float(
                self.casualty_reduction
            ),
            "infrastructure_improvement": float(
                self.infrastructure_improvement
            ),
            "congestion_improvement": float(
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

    Contains:

        baseline result
        every evaluated candidate
        selected intervention
        selection explanation
    """

    baseline: SimulationEvaluation

    candidates: tuple[
        OptimizationCandidateResult,
        ...
    ]

    selected_intervention: (
        Intervention | None
    )

    selection_reason: str

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Return a JSON-compatible representation.
        """

        return {
            "baseline": (
                self.baseline.to_dict()
            ),
            "candidates": [
                candidate.to_dict()
                for candidate
                in self.candidates
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

    The optimizer therefore never:

        - advances the simulation clock
        - calculates flood propagation
        - calculates ML impact
        - calculates infrastructure cascade
        - calculates casualties
        - calculates risk

    Those responsibilities remain inside SimulationEngine and its
    algorithm dependencies.
    """

    def __init__(
        self,
        simulation_provider: (
            SimulationProvider | None
        ) = None,
    ) -> None:

        self.simulation_provider = (
            simulation_provider
        )

    # ------------------------------------------------------------------
    # Public API
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
        Evaluate all applicable interventions against one baseline.

        The baseline is always simulated first with no intervention.

        Every candidate receives an independent simulation run.

        The baseline scenario itself is never mutated.
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

            intervention_scenario = (
                self._build_intervention_scenario(
                    baseline_scenario=(
                        baseline_scenario
                    ),
                    intervention=(
                        candidate.intervention
                    ),
                )
            )

            intervention_result = (
                self.simulation_provider(
                    intervention_scenario
                )
            )

            result = (
                self._compare_candidate(
                    intervention=(
                        candidate.intervention
                    ),
                    baseline=baseline,
                    intervention_result=(
                        intervention_result
                    ),
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

        if not evaluated:

            return OptimizationResult(
                baseline=baseline,
                candidates=(),
                selected_intervention=None,
                selection_reason=(
                    "No applicable intervention "
                    "candidates were available."
                ),
            )

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

    # ------------------------------------------------------------------
    # Candidate comparison
    # ------------------------------------------------------------------

    @staticmethod
    def _compare_candidate(
        *,
        intervention: Intervention,
        baseline: SimulationEvaluation,
        intervention_result: SimulationEvaluation,
    ) -> OptimizationCandidateResult:
        """
        Compare one intervention simulation against baseline.

        Lower is better for:

            risk
            casualties
            infrastructure damage
            congestion

        Therefore each improvement is represented as:

            baseline - intervention

        Positive values mean improvement.
        Negative values mean deterioration.
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

        # --------------------------------------------------------------
        # Weighted optimization objective
        # --------------------------------------------------------------

        improvement_score = (
            risk_reduction * 0.50
            + casualty_reduction * 0.25
            + infrastructure_improvement * 0.15
            + congestion_improvement * 0.10
        )

        rationale = (
            OptimizationEngine
            ._build_rationale(
                intervention=intervention,
                improvement_score=(
                    improvement_score
                ),
                risk_reduction=(
                    risk_reduction
                ),
                casualty_reduction=(
                    casualty_reduction
                ),
                infrastructure_improvement=(
                    infrastructure_improvement
                ),
                congestion_improvement=(
                    congestion_improvement
                ),
            )
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
            risk_reduction=(
                risk_reduction
            ),
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
    # Explanation
    # ------------------------------------------------------------------

    @staticmethod
    def _build_rationale(
        *,
        intervention: Intervention,
        improvement_score: float,
        risk_reduction: float,
        casualty_reduction: float,
        infrastructure_improvement: float,
        congestion_improvement: float,
    ) -> str:
        """
        Build an explainable selection rationale.
        """

        if improvement_score > 0:

            return (
                f"{intervention.name} produced a "
                f"positive simulated improvement score "
                f"of {improvement_score:.2f}. "
                f"Risk changed by "
                f"{risk_reduction:+.2f}, casualties by "
                f"{casualty_reduction:+.2f}, "
                f"infrastructure damage by "
                f"{infrastructure_improvement:+.2f}, "
                f"and congestion by "
                f"{congestion_improvement:+.2f} "
                f"relative to the baseline."
            )

        if improvement_score == 0:

            return (
                f"{intervention.name} produced no "
                "measurable improvement over the "
                "baseline simulation."
            )

        return (
            f"{intervention.name} performed worse "
            "than the baseline simulation according "
            f"to the optimization objective "
            f"({improvement_score:.2f})."
        )

    # ------------------------------------------------------------------
    # Scenario construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_intervention_scenario(
        *,
        baseline_scenario: Mapping[
            str,
            Any,
        ],
        intervention: Intervention,
    ) -> dict[str, Any]:
        """
        Create an independent candidate scenario.

        The original baseline mapping is never mutated.
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
                "OptimizationEngine requires a "
                "simulation provider. Connect it "
                "to SimulationEngine before "
                "running optimization."
            )