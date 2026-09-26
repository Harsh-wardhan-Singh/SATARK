from __future__ import annotations

from typing import Mapping
from simulation.pipeline.base_step import SimulationStep, StepContext


class MetricsStep(SimulationStep):
    """
    Computes global simulation metrics from authoritative engine state.
    Full-fidelity port of _update_basic_metrics.
    """

    @property
    def name(self) -> str:
        return "MetricsStep"

    def execute(self, context: StepContext) -> None:
        # Agent metrics
        if context.agent_manager is not None:
            agents = context.agent_manager.get_agents()

            context.world.state.update_metric(
                "agent_count", float(len(agents))
            )
            context.world.state.update_metric(
                "normal_agents",
                float(len(context.agent_manager.get_normal_agents())),
            )
            context.world.state.update_metric(
                "panicked_agents",
                float(len(context.agent_manager.get_panicked_agents())),
            )
            context.world.state.update_metric(
                "safe_agents",
                float(len(context.agent_manager.get_safe_agents())),
            )

            agent_zone_population = context.agent_manager.get_zone_population()
            context.world.state.environment["agent_zone_population"] = dict(
                agent_zone_population
            )
            context.world.state.update_metric(
                "agent_modeled_population",
                float(sum(agent_zone_population.values())),
            )

        # Active population metric
        active_population = context.world.state.environment.get(
            "active_zone_population", {}
        )
        if isinstance(active_population, Mapping):
            context.world.state.update_metric(
                "active_population",
                float(sum(float(v) for v in active_population.values())),
            )

        # Shelter occupancy metric
        shelter_occupancy = context.world.state.environment.get(
            "shelter_occupancy", {}
        )
        if isinstance(shelter_occupancy, Mapping):
            context.world.state.update_metric(
                "shelter_occupancy",
                float(sum(float(v) for v in shelter_occupancy.values())),
            )

        # Water level metrics
        if context.flood_water_levels:
            water_levels = [float(v) for v in context.flood_water_levels.values()]
            if water_levels:
                context.world.state.update_metric(
                    "max_water_level", float(max(water_levels))
                )
                context.world.state.update_metric(
                    "avg_water_level", float(sum(water_levels) / len(water_levels))
                )

        # Panic metric
        if context.panic_state:
            context.world.state.update_metric(
                "max_panic", float(max(context.panic_state.values()))
            )

        # Casualty metrics
        if context.casualty_state:
            context.world.state.update_metric(
                "total_fatalities",
                float(context.casualty_state.get("total_fatalities", 0)),
            )
            context.world.state.update_metric(
                "total_injuries",
                float(context.casualty_state.get("total_injuries", 0)),
            )

        # Risk metric
        if context.risk_assessment is not None:
            context.world.state.update_metric(
                "composite_risk_score",
                float(context.risk_assessment.composite_risk_score),
            )

        # Decision priority metric
        if context.priority_state:
            priority = context.priority_state.get("overall_priority")
            priority_scores = {
                "LOW": 1.0,
                "MEDIUM": 2.0,
                "HIGH": 3.0,
                "CRITICAL": 4.0,
            }
            if priority in priority_scores:
                context.world.state.update_metric(
                    "decision_priority", priority_scores[priority]
                )

        # Record tick event
        context.world.state.record_event(
            {
                "type": "SIMULATION_TICK",
                "tick": context.clock.current_tick,
            }
        )
