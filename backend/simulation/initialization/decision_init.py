"""
Authoritative Decision & Risk Initialization Subsystem.

Responsible for initializing:
- Risk calculation engine
- Algorithmic and prioritized recommendation engines
- Casualty infrastructure telemetry mapping
"""

from __future__ import annotations

from typing import Any, Mapping

from algorithms.intervention.recommendations import (
    InterventionRuleEngine as AlgorithmRecommendationEngine,
)
from decision.recommendation import RecommendationEngine
from risk.risk_engine import RiskEngine


class DecisionInitializer:
    """
    Encapsulates setup of risk assessment, recommendation generation,
    and casualty-infrastructure data structures.
    """

    @staticmethod
    def initialize_risk_and_decision(
        world: Any,
    ) -> tuple[
        RiskEngine,
        AlgorithmRecommendationEngine,
        RecommendationEngine,
    ]:
        risk_engine = RiskEngine()

        world.state.environment["risk"] = {
            "available": True,
            "assessment": None,
        }

        algo_rec_engine = AlgorithmRecommendationEngine()
        rec_engine = RecommendationEngine()

        world.state.environment["decision"] = {
            "priority": None,
            "recommendations": [],
            "active_interventions": [],
        }

        return (
            risk_engine,
            algo_rec_engine,
            rec_engine,
        )

    @staticmethod
    def build_casualty_infrastructure_data(
        infrastructure_state: Mapping[str, Any],
        infrastructure_network: Any,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Produce normalized infrastructure node list for the casualty engine.
        """
        infrastructure = []

        if infrastructure_state:
            for node_id, node_state in infrastructure_state.items():
                infrastructure.append(
                    {
                        "id": node_id,
                        "type": node_state.get("type", "UNKNOWN") if isinstance(node_state, Mapping) else "UNKNOWN",
                        "zone_id": node_state.get("zone_id") if isinstance(node_state, Mapping) else None,
                    }
                )
        elif infrastructure_network is not None:
            for node_id, node_state in infrastructure_network.nodes.items():
                infrastructure.append(
                    {
                        "id": node_id,
                        "type": node_state.get("type", "UNKNOWN") if isinstance(node_state, Mapping) else "UNKNOWN",
                        "zone_id": node_state.get("zone_id") if isinstance(node_state, Mapping) else None,
                    }
                )

        return {"infrastructure": infrastructure}
