from __future__ import annotations

from typing import Mapping
from simulation.pipeline.base_step import SimulationStep, StepContext


class RiskAssessmentStep(SimulationStep):
    """
    Evaluates overall risk from authoritative simulation outputs.
    Full-fidelity port of _step_risk using the RiskEngine.evaluate() API.
    """

    @property
    def name(self) -> str:
        return "RiskAssessmentStep"

    def execute(self, context: StepContext) -> None:
        if context.risk_engine is None:
            return

        flood_states = context.flood_water_levels
        bottlenecks = context.world.state.environment.get("bottlenecks", {})
        casualties = context.casualty_state
        infrastructure = context.world.state.environment.get("infrastructure", {})

        if not isinstance(flood_states, Mapping):
            flood_states = {}
        if not isinstance(bottlenecks, Mapping):
            bottlenecks = {}
        if not isinstance(casualties, Mapping):
            casualties = {}
        if not isinstance(infrastructure, Mapping):
            infrastructure = {}

        # Determine total population for risk normalization
        active_population = context.world.state.environment.get(
            "active_zone_population", {}
        )

        if isinstance(active_population, Mapping):
            total_population = int(
                round(sum(float(v) for v in active_population.values()))
            )
        else:
            total_population = self._get_base_total_population(context)

        if total_population <= 0:
            total_population = self._get_base_total_population(context)

        context.risk_assessment = context.risk_engine.evaluate(
            casualties=casualties,
            infrastructure=infrastructure,
            flood_states=flood_states,
            bottlenecks=bottlenecks,
            base_total_population=total_population,
        )

        context.risk_state = context.risk_assessment.to_dict()

        context.world.state.environment["risk"] = {
            "available": True,
            "assessment": dict(context.risk_state),
        }

        context.world.state.update_metric(
            "composite_risk_score",
            float(context.risk_assessment.composite_risk_score),
        )

        context.world.state.record_event(
            {
                "type": "RISK_ASSESSMENT_UPDATED",
                "tick": context.clock.current_tick,
                "assessment": dict(context.risk_state),
            }
        )

    def _get_base_total_population(self, context: StepContext) -> int:
        """Derive base total population from population data."""
        if context.population_data is None:
            return 0

        zones = context.population_data.get("zones", [])
        if not isinstance(zones, list):
            return 0

        total = 0
        for zone in zones:
            if not isinstance(zone, Mapping):
                continue
            pop = zone.get("resident_population_estimate", 0)
            try:
                total += int(pop)
            except (TypeError, ValueError):
                continue
        return total
