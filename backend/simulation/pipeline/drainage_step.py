from __future__ import annotations

import logging
from typing import Any
from simulation.pipeline.base_step import SimulationStep, StepContext

logger = logging.getLogger(__name__)


class DrainageStep(SimulationStep):
    """
    Simulates urban stormwater drainage, Manning pipe flow, and mobile pump interventions.
    Executes the CoupledDrainageModel to evaluate surface-drainage dual-layer exchange.
    """

    @property
    def name(self) -> str:
        return "DrainageStep"

    def execute(self, context: StepContext) -> None:
        drainage_boost = 0.0
        zone_pump_boosts: dict[str, float] = {}

        # 1. Parse active mobile pump interventions
        for intervention in context.active_interventions:
            action = intervention.get("action") or intervention.get("id") or intervention.get("intervention_id")
            if action == "deploy_mobile_pumps":
                effect = intervention.get("effect", {})
                boost = float(effect.get("drainage_rate_boost", 0.05))
                drainage_boost += boost

                # Optional zone targets
                target_zones = (
                    intervention.get("target_zones")
                    or intervention.get("zones")
                    or []
                )
                for zid in target_zones:
                    zone_pump_boosts[str(zid)] = (
                        zone_pump_boosts.get(str(zid), 0.0) + boost
                    )

        context.world.state.environment["drainage_boost"] = drainage_boost

        # 2. Execute CoupledDrainageModel if available
        if context.drainage_model is not None:
            drainage_res = context.drainage_model.step(
                water_levels=context.flood_water_levels,
                delta_time=context.delta_time,
                pump_boosts=zone_pump_boosts,
                global_pump_boost=drainage_boost,
            )

            drainage_dict: dict[str, Any] = {
                "total_intake_flow": drainage_res.total_intake_flow,
                "total_conveyed_flow": drainage_res.total_conveyed_flow,
                "total_surcharge_flow": drainage_res.total_surcharge_flow,
                "max_pipe_utilization": drainage_res.max_pipe_utilization,
                "avg_pipe_utilization": drainage_res.avg_pipe_utilization,
                "active_pump_boosts": drainage_res.active_pump_boosts,
                "zone_drainage": {
                    zid: {
                        "intake_rate": s.surface_intake_rate,
                        "surcharge_rate": s.surcharge_rate,
                        "net_drainage_rate": s.net_drainage_rate,
                        "pipe_utilization": s.pipe_utilization,
                        "is_surcharging": s.is_surcharging,
                        "drainage_weakness": s.drainage_weakness,
                    }
                    for zid, s in drainage_res.zone_summaries.items()
                },
            }

            context.drainage_state = drainage_dict
            context.world.state.environment["drainage"] = drainage_dict

            # Update metrics
            context.world.state.update_metric(
                "avg_pipe_utilization", float(drainage_res.avg_pipe_utilization)
            )
            context.world.state.update_metric(
                "total_drainage_surcharge", float(drainage_res.total_surcharge_flow)
            )

            context.world.state.record_event(
                {
                    "type": "DRAINAGE_STEPPED",
                    "tick": context.clock.current_tick,
                    "avg_pipe_utilization": drainage_res.avg_pipe_utilization,
                    "total_surcharge_flow": drainage_res.total_surcharge_flow,
                }
            )
        else:
            context.world.state.environment.setdefault("drainage", {
                "drainage_boost": drainage_boost,
            })
