from __future__ import annotations

from typing import Any, Mapping
from simulation.pipeline.base_step import SimulationStep, StepContext


class InfrastructureCascadeStep(SimulationStep):
    """
    Executes the infrastructure dependency DAG to simulate physical
    and cascading failures. Applies live intervention effects.
    """

    @property
    def name(self) -> str:
        return "InfrastructureCascadeStep"

    def execute(self, context: StepContext) -> None:
        if context.infrastructure_network is None:
            return

        # Apply live intervention effects to infrastructure nodes
        self._apply_interventions(context)

        context.infrastructure_network.simulate_timestep(
            dict(context.flood_impact_scores)
        )

        infrastructure_state: dict[str, dict[str, Any]] = {}

        for node_id, node in context.infrastructure_network.nodes.items():
            capacity = float(node.get("capacity", 1.0))
            reason = str(node.get("status_reason", "Unknown"))

            node_state = {
                "id": node_id,
                "name": node.get("name", node_id),
                "type": node.get("type", "UNKNOWN"),
                "zone_id": node.get("zone_id"),
                "capacity": capacity,
                "status_reason": reason,
            }

            infrastructure_state[node_id] = node_state

            context.world.state.update_metric(
                f"infrastructure_capacity_{node_id}",
                capacity,
            )

        context.infrastructure_state = infrastructure_state

        context.world.state.environment["infrastructure"] = {
            node_id: dict(node_state)
            for node_id, node_state in infrastructure_state.items()
        }

        context.world.state.record_event(
            {
                "type": "INFRASTRUCTURE_STATE_UPDATED",
                "tick": context.clock.current_tick,
                "infrastructure": {
                    node_id: dict(node_state)
                    for node_id, node_state in infrastructure_state.items()
                },
            }
        )

    def _apply_interventions(self, context: StepContext) -> None:
        """Apply backup generator interventions to critical nodes."""
        for intervention in context.active_interventions:
            action = (
                intervention.get("intervention_id")
                or intervention.get("id")
                or intervention.get("action")
            )
            if action == "deploy_backup_generators":
                effect = intervention.get(
                    "expected_effects", intervention.get("effect", {})
                )
                if isinstance(effect, Mapping):
                    floor = float(effect.get("min_capacity_floor", 0.5))
                    for node in context.infrastructure_network.nodes.values():
                        if node.get("type") in ("medical", "power", "water"):
                            node["capacity"] = max(
                                node.get("capacity", 1.0), floor
                            )
