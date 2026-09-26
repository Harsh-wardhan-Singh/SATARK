"""
Authoritative Counterfactual Evaluation Subsystem.

Responsible for:
- Cloning Scenarios with applied Candidate Interventions
- Evaluating candidate scenarios in isolated SimulationEngine containers
- Extracting normalized SimulationEvaluation contracts for OptimizationEngine
"""

from __future__ import annotations

from copy import copy, deepcopy
from dataclasses import is_dataclass, replace
from typing import Any, Mapping

from decision.optimizer import SimulationEvaluation
from simulation.scenario import Scenario
from twin.entity import Entity


class SimulationEvaluator:
    """
    Executes what-if intervention evaluations and translates completed
    simulations into compact SimulationEvaluation metrics.
    """

    @staticmethod
    def clone_scenario_with_intervention(
        scenario: Scenario,
        intervention: Mapping[str, Any] | None,
    ) -> Scenario:
        """
        Produce an isolated Scenario copy with the candidate intervention applied.
        """
        intervention_value = dict(intervention) if intervention is not None else None

        if is_dataclass(scenario):
            try:
                return replace(scenario, intervention=intervention_value)
            except TypeError:
                pass

        scenario_copy = deepcopy(scenario)
        try:
            setattr(scenario_copy, "intervention", intervention_value)
        except (AttributeError, TypeError) as exc:
            raise TypeError(
                "Scenario must support an 'intervention' field for optimization."
            ) from exc

        return scenario_copy

    @staticmethod
    def clone_initial_entities(entities: list[Entity]) -> list[Entity]:
        """
        Clone initial Digital Twin entities for candidate scenario runs.
        Uses fast copy to avoid Python deepcopy overhead across hundreds of agents.
        """
        cloned: list[Entity] = []
        for entity in entities:
            try:
                # Fast shallow copy with new position
                c = copy(entity)
                if hasattr(entity, "position") and entity.position is not None:
                    c.position = copy(entity.position)
                cloned.append(c)
            except Exception:
                cloned.append(deepcopy(entity))
        return cloned

    @classmethod
    def provide_simulation_evaluation(
        cls,
        engine_cls: type,
        scenario_payload: Mapping[str, Any] | None,
        base_scenario: Scenario,
        initial_entities: list[Entity],
        cached_zone_mapping: dict[str, Any] | None = None,
    ) -> SimulationEvaluation:
        """
        Execute one isolated scenario and return its SimulationEvaluation.
        """
        if scenario_payload is None:
            supplied_scenario = base_scenario
            intervention = None
        else:
            supplied_scenario = scenario_payload.get("scenario", base_scenario)
            if not isinstance(supplied_scenario, Scenario):
                raise TypeError(
                    "Optimization scenario payload must contain a Scenario under 'scenario'."
                )
            intervention = scenario_payload.get("intervention")

        evaluation_scenario = cls.clone_scenario_with_intervention(
            supplied_scenario,
            intervention,
        )

        evaluation_engine = engine_cls(
            scenario=evaluation_scenario,
            entities=cls.clone_initial_entities(initial_entities),
        )

        if cached_zone_mapping:
            evaluation_engine._cached_zone_mapping = dict(cached_zone_mapping)

        evaluation_engine.initialize()

        while not evaluation_engine.is_complete:
            evaluation_engine.step()

        return cls.build_simulation_evaluation(evaluation_engine)

    @staticmethod
    def build_simulation_evaluation(engine: Any) -> SimulationEvaluation:
        """
        Derive SimulationEvaluation from a completed SimulationEngine instance.
        """
        final_risk_score = 0.0
        if engine._risk_assessment is not None:
            final_risk_score = float(engine._risk_assessment.composite_risk_score)

        fatalities = float(
            engine._casualty_state.get(
                "total_fatalities",
                engine.world.state.metrics.get("total_fatalities", 0.0),
            )
        )

        injuries = float(
            engine._casualty_state.get(
                "total_injuries",
                engine.world.state.metrics.get("total_injuries", 0.0),
            )
        )

        total_casualties = fatalities + injuries

        # Infrastructure damage
        infra_state = engine._infrastructure_state or {}
        capacities = [
            max(0.0, min(1.0, float(n.get("capacity", 1.0))))
            for n in infra_state.values()
            if isinstance(n, Mapping)
        ]
        infrastructure_damage = (
            max(0.0, min(1.0, 1.0 - (sum(capacities) / len(capacities))))
            if capacities
            else 0.0
        )

        # Congestion
        bottlenecks = engine.world.state.environment.get("bottlenecks", {})
        values = (
            [max(0.0, float(v)) for v in bottlenecks.values() if isinstance(v, (int, float))]
            if isinstance(bottlenecks, Mapping)
            else []
        )
        congestion = max(0.0, min(1.0, max(values))) if values else 0.0

        metrics = {
            key: float(value)
            for key, value in engine.world.state.metrics.items()
        }

        additional_data = {
            "current_tick": engine.clock.current_tick,
            "simulation_time": engine.clock.simulation_time,
            "severity": (
                engine._risk_assessment.severity_label
                if engine._risk_assessment is not None
                else None
            ),
            "risk_breakdown": (
                dict(engine._risk_assessment.breakdown)
                if engine._risk_assessment is not None
                else {}
            ),
            "fatalities": fatalities,
            "injuries": injuries,
            "active_intervention": (
                dict(engine._active_interventions[-1])
                if engine._active_interventions
                else None
            ),
            "active_interventions": [dict(i) for i in engine._active_interventions],
        }

        drainage_state = engine.world.state.environment.get("drainage", {})
        total_surcharge_m3 = float(drainage_state.get("total_surcharge_volume_m3", 0.0))

        water_levels = engine.world.state.environment.get("flood_water_levels", {})
        peak_depth_m = max(water_levels.values()) if water_levels else 0.0
        peak_depth_cm = round(peak_depth_m * 100.0, 2)
        critical_zones = sum(1 for d in water_levels.values() if d >= 0.30)

        return SimulationEvaluation(
            metrics=metrics,
            final_risk_score=final_risk_score,
            casualties=total_casualties,
            infrastructure_damage=infrastructure_damage,
            congestion=congestion,
            total_surcharge_m3=total_surcharge_m3,
            peak_water_depth_cm=peak_depth_cm,
            critical_zones_count=critical_zones,
            additional_data=additional_data,
        )
