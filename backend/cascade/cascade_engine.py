from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping

from cascade.graph import DependencyGraph


@dataclass(frozen=True)
class CascadeResult:
    """
    Structured result of one infrastructure cascade evaluation.

    This is a result object, not the authoritative world state.

    The simulation layer can later apply these capacities/statuses
    to the Digital Twin.
    """

    node_states: Dict[str, Dict[str, Any]]

    affected_nodes: list[str] = field(
        default_factory=list
    )

    failed_nodes: list[str] = field(
        default_factory=list
    )

    critical_failures: list[str] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a JSON-compatible representation.
        """

        return {
            "node_states": {
                node_id: dict(state)
                for node_id, state
                in self.node_states.items()
            },
            "affected_nodes": list(
                self.affected_nodes
            ),
            "failed_nodes": list(
                self.failed_nodes
            ),
            "critical_failures": list(
                self.critical_failures
            ),
        }


class CascadeEngine:
    """
    Calculates secondary infrastructure failures.

    Input:

        zone-level disaster impact

    Output:

        CascadeResult

    The engine does not modify WorldState.

    It also does not modify Building/Road/Facility objects directly.

    The simulation layer will eventually decide when and how to apply
    the result to the authoritative Digital Twin.
    """

    def __init__(
        self,
        infrastructure_data: Mapping[str, Any],
    ) -> None:

        self.infrastructure_data = {
            "infrastructure": [
                dict(node)
                for node in infrastructure_data.get(
                    "infrastructure",
                    [],
                )
            ]
        }

        self.graph = DependencyGraph(
            self.infrastructure_data
        )

    # ------------------------------------------------------------------
    # Main cascade operation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        impact_by_zone: Mapping[str, float],
    ) -> CascadeResult:
        """
        Evaluate infrastructure degradation caused by disaster impact.

        Args:
            impact_by_zone:
                Mapping:

                    zone_id -> impact score

                Impact must be in the range [0, 1].

        Returns:
            CascadeResult
        """

        normalized_impacts = (
            self._normalize_impacts(
                impact_by_zone
            )
        )

        node_states: Dict[
            str,
            Dict[str, Any],
        ] = {}

        # --------------------------------------------------------------
        # Process infrastructure in dependency order.
        #
        # Parents are evaluated before dependent children.
        # This makes cascade propagation deterministic and avoids
        # repeatedly mutating the same state until convergence.
        # --------------------------------------------------------------

        for node_id in (
            self.graph.topological_order()
        ):
            node = self.graph.get_node(
                node_id
            )

            zone_id = node.get(
                "zone_id"
            )

            impact = normalized_impacts.get(
                zone_id,
                0.0,
            )

            vulnerability_threshold = float(
                node.get(
                    "vulnerability_threshold",
                    1.0,
                )
            )

            backup_power = self._clamp(
                float(
                    node.get(
                        "backup_power",
                        0.0,
                    )
                )
            )

            # ----------------------------------------------------------
            # 1. Direct disaster impact
            # ----------------------------------------------------------

            local_health = self._calculate_local_health(
                impact=impact,
                threshold=vulnerability_threshold,
            )

            # ----------------------------------------------------------
            # 2. Dependency impact
            # ----------------------------------------------------------

            dependencies = self.graph.get_parents(
                node_id
            )

            dependency_health = (
                self._calculate_dependency_health(
                    dependencies=dependencies,
                    node_states=node_states,
                    backup_power=backup_power,
                )
            )

            # ----------------------------------------------------------
            # 3. Final operational capacity
            # ----------------------------------------------------------

            final_capacity = self._clamp(
                local_health
                * dependency_health
            )

            reason = self._determine_reason(
                impact=impact,
                local_health=local_health,
                dependency_health=dependency_health,
                node_states=node_states,
                dependencies=dependencies,
                threshold=vulnerability_threshold,
            )

            status = self._status_from_capacity(
                final_capacity
            )

            node_states[node_id] = {
                "zone_id": zone_id,
                "type": node.get(
                    "type",
                    "unknown",
                ),
                "name": node.get(
                    "name",
                    node_id,
                ),
                "capacity": final_capacity,
                "capacity_percent": round(
                    final_capacity * 100.0,
                    1,
                ),
                "status": status,
                "reason": reason,
                "impact": impact,
                "local_health": local_health,
                "dependency_health": dependency_health,
            }

        return self._build_result(
            node_states
        )

    # ------------------------------------------------------------------
    # Direct impact
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_local_health(
        *,
        impact: float,
        threshold: float,
    ) -> float:
        """
        Calculate direct infrastructure health.

        This preserves the explainable cascade model already present
        in algorithms/infrastructure/cascade.py:

            if impact <= threshold:
                health = 1

            otherwise:
                damage = (impact - threshold) * 2

                health = max(0, 1 - damage)
        """

        if impact <= threshold:
            return 1.0

        damage = (
            impact - threshold
        ) * 2.0

        return max(
            0.0,
            1.0 - damage,
        )

    # ------------------------------------------------------------------
    # Dependency impact
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_dependency_health(
        *,
        dependencies: list[Dict[str, Any]],
        node_states: Mapping[
            str,
            Mapping[str, Any],
        ],
        backup_power: float,
    ) -> float:
        """
        Calculate the health supplied by infrastructure dependencies.

        Each dependency contributes:

            parent_capacity * dependency_weight

        Backup power provides a floor/blending factor:

            backup_power
            +
            (1 - backup_power) * dependency_score
        """

        if not dependencies:
            return 1.0

        total_weight = sum(
            float(
                dependency.get(
                    "weight",
                    1.0,
                )
            )
            for dependency in dependencies
        )

        if total_weight <= 0:
            return 1.0

        dependency_score = 0.0

        for dependency in dependencies:
            parent_id = dependency[
                "parent_id"
            ]

            weight = float(
                dependency.get(
                    "weight",
                    1.0,
                )
            )

            parent_state = node_states.get(
                parent_id
            )

            parent_capacity = 1.0

            if parent_state is not None:
                parent_capacity = float(
                    parent_state.get(
                        "capacity",
                        1.0,
                    )
                )

            dependency_score += (
                parent_capacity
                * weight
            )

        dependency_score /= total_weight

        return (
            backup_power
            + (
                1.0 - backup_power
            )
            * dependency_score
        )

    # ------------------------------------------------------------------
    # Explainability
    # ------------------------------------------------------------------

    @staticmethod
    def _determine_reason(
        *,
        impact: float,
        local_health: float,
        dependency_health: float,
        node_states: Mapping[
            str,
            Mapping[str, Any],
        ],
        dependencies: list[Dict[str, Any]],
        threshold: float,
    ) -> str:
        """
        Explain the primary reason for the node's current state.
        """

        final_capacity = (
            local_health
            * dependency_health
        )

        if final_capacity > 0.9:
            return "Fully Operational"

        if local_health < dependency_health:
            return (
                "Direct Flood Damage "
                f"(Impact: {impact:.2f})"
            )

        for dependency in dependencies:
            parent_id = dependency[
                "parent_id"
            ]

            parent_state = node_states.get(
                parent_id
            )

            if parent_state is None:
                continue

            if float(
                parent_state.get(
                    "capacity",
                    1.0,
                )
            ) < 0.5:
                parent_name = parent_state.get(
                    "name",
                    parent_id,
                )

                return (
                    "Cascading failure: "
                    f"Lost connection to {parent_name}"
                )

        if impact > threshold:
            return (
                "Direct infrastructure degradation"
            )

        if dependency_health < 1.0:
            return (
                "Cascading dependency degradation"
            )

        return "Degraded performance"

    # ------------------------------------------------------------------
    # Result construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_result(
        node_states: Dict[
            str,
            Dict[str, Any],
        ],
    ) -> CascadeResult:
        """
        Build the structured cascade result.
        """

        affected_nodes = [
            node_id
            for node_id, state
            in node_states.items()
            if float(
                state["capacity"]
            ) < 1.0
        ]

        failed_nodes = [
            node_id
            for node_id, state
            in node_states.items()
            if float(
                state["capacity"]
            ) <= 0.0
        ]

        critical_failures = [
            node_id
            for node_id, state
            in node_states.items()
            if float(
                state["capacity"]
            ) < 0.5
        ]

        return CascadeResult(
            node_states=node_states,
            affected_nodes=affected_nodes,
            failed_nodes=failed_nodes,
            critical_failures=critical_failures,
        )

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_impacts(
        impact_by_zone: Mapping[str, float],
    ) -> Dict[str, float]:
        """
        Validate and clamp zone impact values.
        """

        normalized: Dict[
            str,
            float,
        ] = {}

        for zone_id, impact in (
            impact_by_zone.items()
        ):
            value = float(
                impact
            )

            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    "Impact for zone "
                    f"'{zone_id}' must be within [0, 1]."
                )

            normalized[
                str(zone_id)
            ] = value

        return normalized

    @staticmethod
    def _status_from_capacity(
        capacity: float,
    ) -> str:
        """
        Convert operational capacity into a simple cascade status.

        This is intentionally separate from the infrastructure entity's
        InfrastructureStatus enum. The simulation integration phase will
        decide how/when this result maps onto live infrastructure state.
        """

        if capacity <= 0.0:
            return "FAILED"

        if capacity < 0.5:
            return "CRITICAL"

        if capacity < 0.9:
            return "DEGRADED"

        return "OPERATIONAL"

    @staticmethod
    def _clamp(
        value: float,
    ) -> float:
        return max(
            0.0,
            min(
                1.0,
                value,
            ),
        )
    
