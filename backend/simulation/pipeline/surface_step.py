from __future__ import annotations

import logging
from simulation.pipeline.base_step import SimulationStep, StepContext

logger = logging.getLogger(__name__)


class SurfaceFloodStep(SimulationStep):
    """
    Steps the authoritative flood simulation model, updates water levels,
    computes per-zone water metrics, and stores into WorldState environment.
    """

    @property
    def name(self) -> str:
        return "SurfaceFloodStep"

    def execute(self, context: StepContext) -> None:
        if context.flood is None:
            return

        # Apply live intervention effects to flood (drainage boost)
        self._apply_flood_interventions(context)

        flood_state = context.flood.step(context.delta_time)
        water_levels = flood_state.get("water_levels", {})
        water_levels_cm = flood_state.get("water_levels_cm", {})

        num_flooded = len([v for v in water_levels.values() if v > 0])
        max_level = max(water_levels.values()) if water_levels else 0.0
        max_level_cm = max(water_levels_cm.values()) if water_levels_cm else 0.0

        logger.debug(
            "[FLOOD STEP] dt=%.3f t=%.2f rain=%.2f flooded=%d max=%.3fm (%.1fcm)",
            context.delta_time,
            context.clock.simulation_time,
            context.scenario.rainfall_intensity,
            num_flooded,
            max_level,
            max_level_cm,
        )

        context.flood_water_levels = dict(water_levels)
        context.world.state.environment["flood_water_levels"] = dict(water_levels)
        context.world.state.environment["flood_water_levels_cm"] = dict(water_levels_cm)
        if context.flood is not None:
            context.world.state.environment["rainfall_intensity"] = (
                context.flood.rainfall_intensity
            )
        else:
            context.world.state.environment["rainfall_intensity"] = (
                context.scenario.rainfall_intensity
            )

        for zone_id, water_level in water_levels.items():
            context.world.state.update_metric(
                f"flood_water_{zone_id}", float(water_level)
            )

        for zone_id, water_cm in water_levels_cm.items():
            context.world.state.update_metric(
                f"flood_water_cm_{zone_id}", float(water_cm)
            )

        context.world.state.update_metric("max_water_level_cm", float(max_level_cm))

    def _apply_flood_interventions(self, context: StepContext) -> None:
        """Apply live intervention drainage boosts to the flood model."""
        for intervention in context.active_interventions:
            action = (
                intervention.get("intervention_id")
                or intervention.get("id")
                or intervention.get("action")
            )
            if action == "deploy_mobile_pumps":
                effect = intervention.get(
                    "expected_effects", intervention.get("effect", {})
                )
                if isinstance(effect, dict):
                    boost = float(effect.get("drainage_rate_boost", 0.05))
                    if hasattr(context.flood, "apply_drainage_boost"):
                        context.flood.apply_drainage_boost(boost)
