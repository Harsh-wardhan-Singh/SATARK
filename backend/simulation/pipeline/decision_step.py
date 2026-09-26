from __future__ import annotations

from typing import Any, Mapping
from simulation.pipeline.base_step import SimulationStep, StepContext


class DecisionInterventionStep(SimulationStep):
    """
    Evaluates zone priorities, generates algorithm recommendations,
    and wraps them into the decision-layer Recommendation objects.
    Full-fidelity port of _step_decision.
    """

    @property
    def name(self) -> str:
        return "DecisionInterventionStep"

    def execute(self, context: StepContext) -> None:
        if context.risk_assessment is None:
            return

        risk_assessment = dict(context.risk_state)

        # ------------------------------------------------------------------
        # 1. Priority evaluation
        # ------------------------------------------------------------------

        if context.recommendation_engine is not None:
            priority_result = context.recommendation_engine.priority_engine.evaluate(
                risk_assessment
            )
            context.priority_state = priority_result.to_dict()
        else:
            context.priority_state = {}

        context.world.state.environment["decision"] = {
            "priority": dict(context.priority_state),
            "recommendations": [],
            "active_interventions": [dict(i) for i in context.active_interventions],
        }

        # ------------------------------------------------------------------
        # 2. Algorithm recommendations (InterventionRuleEngine)
        # ------------------------------------------------------------------

        applied_ids = [
            str(
                i.get("intervention_id", i.get("id", i.get("action", "")))
            )
            for i in context.active_interventions
        ]

        raw_recommendations: list[Any] = []
        if context.intervention_rule_engine is not None:
            raw_recommendations = (
                context.intervention_rule_engine.generate_recommendations(
                    risk_assessment,
                    applied_intervention_ids=applied_ids,
                )
            )

        # ------------------------------------------------------------------
        # 3. Decision-layer adapter (RecommendationEngine)
        # ------------------------------------------------------------------

        if context.recommendation_engine is not None:
            context.recommendations = context.recommendation_engine.recommend(
                risk_assessment=risk_assessment,
                algorithm_recommendations=raw_recommendations,
            )
        else:
            context.recommendations = list(raw_recommendations)

        recommendation_state = [
            rec.to_dict() if hasattr(rec, "to_dict") else dict(rec)
            for rec in context.recommendations
        ]

        context.world.state.environment["decision"] = {
            "priority": dict(context.priority_state),
            "recommendations": recommendation_state,
            "active_interventions": [dict(i) for i in context.active_interventions],
        }

        # ------------------------------------------------------------------
        # 4. Explicit scenario intervention (auto-apply once)
        # ------------------------------------------------------------------

        if context.scenario.intervention is not None:
            intervention_id = str(
                context.scenario.intervention.get(
                    "intervention_id",
                    context.scenario.intervention.get(
                        "id",
                        context.scenario.intervention.get("action"),
                    ),
                )
            )

            already_applied = any(
                str(
                    i.get("intervention_id", i.get("id", i.get("action")))
                )
                == intervention_id
                for i in context.active_interventions
            )

            if intervention_id and not already_applied:
                # Scenario interventions are applied by the engine's
                # apply_intervention() API, not by the pipeline step.
                # We only flag the need; the engine handles application.
                context.world.state.environment.setdefault(
                    "_pending_scenario_intervention",
                    context.scenario.intervention,
                )

        context.world.state.record_event(
            {
                "type": "DECISION_STATE_UPDATED",
                "tick": context.clock.current_tick,
                "priority": dict(context.priority_state),
                "recommendations": recommendation_state,
                "active_interventions": [
                    dict(i) for i in context.active_interventions
                ],
            }
        )
