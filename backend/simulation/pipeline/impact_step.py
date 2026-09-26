from __future__ import annotations

from simulation.pipeline.base_step import SimulationStep, StepContext


class FloodImpactStep(SimulationStep):
    """
    Computes ML-based zone impact scores from surface flood water levels.
    Uses flood_zone_data and scenario parameters for feature engineering.
    """

    @property
    def name(self) -> str:
        return "FloodImpactStep"

    def execute(self, context: StepContext) -> None:
        if context.flood_impact is None:
            return

        if not context.flood_water_levels:
            return

        day = max(
            1,
            int(context.clock.simulation_time / 86400.0) + 1,
        )

        impact_scores = context.flood_impact.calculate_impacts(
            context.flood_water_levels,
            context.flood_zone_data,
            severity=context.scenario.severity,
            day=day,
            intervention_level=context.scenario.intervention_level,
            drainage_state=context.drainage_state,
        )

        context.flood_impact_scores = dict(impact_scores)
        context.world.state.environment["flood_impact_scores"] = dict(impact_scores)

        for zone_id, impact in impact_scores.items():
            context.world.state.update_metric(
                f"flood_impact_{zone_id}", float(impact)
            )

        context.world.state.record_event(
            {
                "type": "FLOOD_STATE_UPDATED",
                "tick": context.clock.current_tick,
                "water_levels": dict(context.flood_water_levels),
                "impact_scores": dict(impact_scores),
            }
        )
