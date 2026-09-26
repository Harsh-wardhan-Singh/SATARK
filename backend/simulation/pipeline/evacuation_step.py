from __future__ import annotations

from typing import Any, Mapping
from infrastructure.facility import Facility
from simulation.pipeline.base_step import SimulationStep, StepContext


class HumanEvacuationStep(SimulationStep):
    """
    Simulates panic escalation, dynamic evacuation routes, crowd bottlenecks,
    agent physical movement, shelter intake reconciliation, and casualty estimation.

    This is the full-fidelity port of the monolithic _step_human_response.
    """

    @property
    def name(self) -> str:
        return "HumanEvacuationStep"

    def execute(self, context: StepContext) -> None:
        if not context.human_response_enabled:
            return

        if context.panic_engine is None:
            return

        context.panic_accumulator += context.delta_time

        if context.panic_accumulator < context.population_model_step_seconds:
            return

        context.panic_accumulator = (
            context.panic_accumulator % context.population_model_step_seconds
        )

        flood_states = dict(context.flood_water_levels)
        flood_impacts = dict(context.flood_impact_scores)

        # ------------------------------------------------------------------
        # 1. Panic
        # ------------------------------------------------------------------

        panic_state = context.panic_engine.update_panic(
            flood_impacts=flood_impacts,
            infra_states=context.infrastructure_state,
        )
        context.panic_state = dict(panic_state)
        context.world.state.environment["panic_by_zone"] = dict(panic_state)

        for zone_id, panic_level in panic_state.items():
            context.world.state.update_metric(
                f"panic_{zone_id}", float(panic_level)
            )

        # ------------------------------------------------------------------
        # 2. Evacuation Routes
        # ------------------------------------------------------------------

        if context.evacuation_engine is not None:
            effective_flood = self._build_effective_flood(context, flood_states)
            context.world.state.environment["evacuation_hazard_states"] = dict(
                effective_flood
            )

            evac_result = context.evacuation_engine.calculate_evacuation_routes(
                flood_states=dict(effective_flood),
                panic_states=dict(context.panic_state),
            )

            if (
                isinstance(evac_result, Mapping)
                and evac_result.get("status") == "CRITICAL"
            ):
                context.evacuation_routes = {}
            else:
                context.evacuation_routes = dict(evac_result)

                # Assign routes to individual agents
                if context.agent_manager is not None and context.cached_zone_mapping:
                    assigned = context.agent_manager.assign_evacuation_routes(
                        context.evacuation_routes,
                        zone_mapping=context.cached_zone_mapping,
                    )
                    context.world.state.update_metric(
                        "agents_with_evacuation_routes", float(assigned)
                    )

            context.world.state.environment["evacuation_routes"] = dict(
                context.evacuation_routes
            )

        # ------------------------------------------------------------------
        # 3. Agent Panic & Movement
        # ------------------------------------------------------------------

        safe_centers = [
            entity
            for entity in context.world.state.get_entities()
            if isinstance(entity, Facility)
            and entity.is_safe_center
            and entity.is_operational
            and entity.available_capacity > 0
        ]

        transitioned = 0

        if context.agent_manager is not None:
            transitioned = context.agent_manager.trigger_panic_for_zones(
                panic_by_zone=context.panic_state,
                safe_centers=safe_centers,
                threshold=context.panic_threshold,
            )

            # Advance agent positions with intervention speed multiplier
            self._update_agents(context, safe_centers)

            # Reconcile shelter intake
            self._reconcile_shelter_intake(context)

        # ------------------------------------------------------------------
        # 4. Crowd Dynamics
        # ------------------------------------------------------------------

        if context.crowd_engine is not None:
            self._apply_crowd_interventions(context)

            crowd_panic_states = self._get_effective_crowd_panic_states(context)

            context.crowd_state = context.crowd_engine.simulate_movement_step(
                evacuation_routes=context.evacuation_routes,
                panic_states=crowd_panic_states,
            )

            context.world.state.environment["crowd"] = dict(context.crowd_state)

            context.world.state.environment["shelter_occupancy"] = {
                str(shelter_id): float(
                    shelter.get("current_occupancy", 0.0)
                )
                for shelter_id, shelter in context.crowd_engine.shelters.items()
                if isinstance(shelter, Mapping)
            }

            bottlenecks = context.crowd_state.get("bottlenecks", {})
            if isinstance(bottlenecks, Mapping):
                context.world.state.environment["bottlenecks"] = dict(bottlenecks)
                for zone_id, value in bottlenecks.items():
                    context.world.state.update_metric(
                        f"bottleneck_{zone_id}", float(value)
                    )

        # ------------------------------------------------------------------
        # 5. Casualties
        # ------------------------------------------------------------------

        if context.casualties_engine is not None:
            current_populations = self._get_current_populations(context)

            bottlenecks = context.crowd_state.get("bottlenecks", {})

            context.casualty_state = context.casualties_engine.update_casualties(
                current_populations=current_populations,
                flood_states=dict(flood_states),
                bottlenecks=dict(bottlenecks),
                panic_states=dict(context.panic_state),
                infra_states=context.infrastructure_state,
                time_step_seconds=context.delta_time,
            )

            context.world.state.environment["casualties"] = dict(
                context.casualty_state
            )

            context.world.state.update_metric(
                "total_fatalities",
                float(context.casualty_state.get("total_fatalities", 0)),
            )
            context.world.state.update_metric(
                "total_injuries",
                float(context.casualty_state.get("total_injuries", 0)),
            )

            self._apply_cumulative_casualty_reduction(context)

        context.world.state.record_event(
            {
                "type": "HUMAN_RESPONSE_UPDATED",
                "tick": context.clock.current_tick,
                "panic_by_zone": dict(context.panic_state),
                "evacuation_routes": dict(context.evacuation_routes),
                "agents_transitioned_to_panic": transitioned,
                "crowd": dict(context.crowd_state),
                "casualties": dict(context.casualty_state),
            }
        )

    # ------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------

    def _build_effective_flood(
        self, context: StepContext, flood_states: Mapping[str, float]
    ) -> dict[str, float]:
        """
        Translate infrastructure degradation into additional evacuation
        hazard while keeping the existing Dijkstra implementation authoritative.
        """
        effective = {
            str(z): max(0.0, min(1.0, float(v)))
            for z, v in flood_states.items()
        }

        route_capacities: dict[str, list[float]] = {}

        for node_state in context.infrastructure_state.values():
            zone_id = node_state.get("zone_id") if isinstance(node_state, Mapping) else None
            if not zone_id or zone_id not in effective:
                continue

            cap = float(node_state.get("capacity", 1.0))
            route_capacities.setdefault(zone_id, []).append(cap)

        for zone_id, caps in route_capacities.items():
            if not caps:
                continue
            min_cap = min(caps)
            if min_cap < 0.5:
                penalty = (0.5 - min_cap) * 0.4
                effective[zone_id] = min(1.0, effective[zone_id] + penalty)

        return effective

    def _update_agents(
        self, context: StepContext, safe_centers: list[Any]
    ) -> None:
        """Advance agent positions with intervention speed multiplier."""
        if context.agent_manager is None:
            return

        movement_multiplier = self._get_movement_speed_multiplier(context)

        panic_behaviors: list[tuple[Any, float]] = []

        if movement_multiplier != 1.0:
            for agent in context.agent_manager.get_panicked_agents():
                behavior = agent.panic_behavior
                original_speed = behavior.speed
                behavior.speed = original_speed * movement_multiplier
                panic_behaviors.append((behavior, original_speed))

        try:
            context.agent_manager.update_all(
                delta_time=context.delta_time,
                safe_centers=safe_centers,
                zone_mapping=context.cached_zone_mapping or {},
            )
        finally:
            for behavior, original_speed in panic_behaviors:
                behavior.speed = original_speed

    def _get_movement_speed_multiplier(self, context: StepContext) -> float:
        """Extract movement speed multiplier from active interventions."""
        for intervention in reversed(context.active_interventions):
            action = (
                intervention.get("intervention_id")
                or intervention.get("id")
                or intervention.get("action", "")
            )
            if str(action) == "mandatory_evacuation_order":
                effect = intervention.get(
                    "expected_effects", intervention.get("effect", {})
                )
                if isinstance(effect, Mapping):
                    return float(effect.get("movement_speed_multiplier", 1.0))
        return 1.0

    def _reconcile_shelter_intake(self, context: StepContext) -> None:
        """
        Reconcile SAFE HumanAgent intake with the existing crowd shelter
        state without double-counting people already admitted.
        """
        if context.agent_manager is None or context.crowd_engine is None:
            return

        intake = context.agent_manager.register_safe_agent_intake()
        if not intake:
            return

        for shelter_id, amount in intake.items():
            shelter = context.crowd_engine.shelters.get(shelter_id)
            if not isinstance(shelter, Mapping):
                continue

            current = float(shelter.get("current_occupancy", 0.0))
            capacity = float(shelter.get("capacity", 0.0))
            reconciled = min(capacity, max(current, float(amount)))
            shelter["current_occupancy"] = reconciled

        context.world.state.environment["shelter_agent_intake"] = dict(intake)

    def _apply_crowd_interventions(self, context: StepContext) -> None:
        """Apply traffic rerouting interventions to crowd engine."""
        for intervention in context.active_interventions:
            action = (
                intervention.get("intervention_id")
                or intervention.get("id")
                or intervention.get("action")
            )
            if action == "reroute_traffic":
                effect = intervention.get(
                    "expected_effects", intervention.get("effect", {})
                )
                if isinstance(effect, Mapping):
                    multiplier = float(effect.get("capacity_multiplier", 1.0))
                    if hasattr(context.crowd_engine, "apply_capacity_multiplier"):
                        context.crowd_engine.apply_capacity_multiplier(multiplier)

    def _get_effective_crowd_panic_states(
        self, context: StepContext
    ) -> dict[str, float]:
        """
        Convert mandatory evacuation intervention into effective panic
        movement rate used by the crowd dynamics algorithm.
        """
        panic_states = dict(context.panic_state)

        if not context.active_interventions:
            return panic_states

        intervention = next(
            (
                i
                for i in reversed(context.active_interventions)
                if str(
                    i.get("intervention_id", i.get("id", i.get("action", "")))
                )
                == "mandatory_evacuation_order"
            ),
            None,
        )
        if not intervention:
            return panic_states

        effect = intervention.get(
            "expected_effects", intervention.get("effect", {})
        )
        if not isinstance(effect, Mapping):
            return panic_states

        multiplier = float(effect.get("movement_speed_multiplier", 1.0))
        if multiplier <= 1.0:
            return panic_states

        effective = {}
        for zone_id, panic in panic_states.items():
            base_rate = 0.4 + (0.4 * float(panic))
            target_rate = min(1.0, base_rate * multiplier)
            effective_panic = (target_rate - 0.4) / 0.4
            effective[str(zone_id)] = max(0.0, min(1.0, effective_panic))

        return effective

    def _get_current_populations(
        self, context: StepContext
    ) -> dict[str, float]:
        """Get current zone populations from crowd engine or agent manager."""
        if context.crowd_engine is not None:
            populations = {
                str(zone_id): float(population)
                for zone_id, population in context.crowd_engine.zone_populations.items()
            }
            context.world.state.environment["zone_population"] = dict(populations)
            context.world.state.environment["active_zone_population"] = dict(
                populations
            )
            context.world.state.update_metric(
                "active_population",
                float(sum(populations.values())),
            )
            return populations

        if context.agent_manager is not None:
            return {
                zone_id: float(population)
                for zone_id, population in context.agent_manager.get_zone_population().items()
            }

        return {}

    def _apply_cumulative_casualty_reduction(
        self, context: StepContext
    ) -> None:
        """
        Remove cumulative fatalities from active crowd populations.
        CasualtiesEngine owns cumulative casualty estimation.
        CrowdDynamicsEngine owns population movement.
        """
        if context.crowd_engine is None:
            return

        breakdown = (
            context.casualty_state.get("zone_breakdown", {})
            if isinstance(context.casualty_state, Mapping)
            else {}
        )

        if not isinstance(breakdown, Mapping):
            return

        for zone_id, casualty_zone in breakdown.items():
            if not isinstance(casualty_zone, Mapping):
                continue

            try:
                cumulative_fatalities = max(
                    0.0, float(casualty_zone.get("fatalities", 0.0))
                )
            except (TypeError, ValueError):
                continue

            zone_key = str(zone_id)
            previous = context.casualty_population_reduction.get(zone_key, 0.0)
            newly_removed = max(0.0, cumulative_fatalities - previous)

            context.casualty_population_reduction[zone_key] = cumulative_fatalities

            if newly_removed <= 0:
                continue

            current = float(
                context.crowd_engine.zone_populations.get(zone_id, 0.0)
            )
            context.crowd_engine.zone_populations[zone_id] = max(
                0.0, current - newly_removed
            )

        active_population = {
            str(zone_id): float(population)
            for zone_id, population in context.crowd_engine.zone_populations.items()
        }

        context.world.state.environment["active_zone_population"] = dict(
            active_population
        )
        context.world.state.update_metric(
            "active_population",
            float(sum(active_population.values())),
        )
