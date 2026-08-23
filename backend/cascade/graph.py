from __future__ import annotations

from collections import deque
from typing import Any, Dict, Iterable, List, Mapping, Set


class DependencyGraph:
    """
    Directed infrastructure dependency graph.

    An edge:

        parent -> child

    means that the child depends on the parent.

    Example:

        power_station -> hospital

    means the hospital depends on the power station.

    The graph contains infrastructure IDs and dependency weights.
    It does not own live infrastructure state.
    """

    def __init__(
        self,
        infrastructure_data: Mapping[str, Any],
    ) -> None:
        nodes = infrastructure_data.get(
            "infrastructure",
            []
        )

        if not isinstance(nodes, list):
            raise ValueError(
                "'infrastructure' must be a list."
            )

        self.nodes: Dict[str, Dict[str, Any]] = {}

        for node in nodes:
            node_id = node.get("id")

            if not node_id:
                raise ValueError(
                    "Every infrastructure node must have an id."
                )

            if node_id in self.nodes:
                raise ValueError(
                    f"Duplicate infrastructure id: {node_id}"
                )

            self.nodes[node_id] = dict(node)

        self.children: Dict[str, List[str]] = {
            node_id: []
            for node_id in self.nodes
        }

        self.parents: Dict[str, List[Dict[str, Any]]] = {
            node_id: []
            for node_id in self.nodes
        }

        self._build_graph()

        self.validate()

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> None:
        """
        Build parent -> child relationships from depends_on.
        """

        for node_id, node in self.nodes.items():
            dependencies = node.get(
                "depends_on",
                []
            )

            if dependencies is None:
                dependencies = []

            if not isinstance(
                dependencies,
                list,
            ):
                raise ValueError(
                    f"'depends_on' for '{node_id}' "
                    "must be a list."
                )

            for dependency in dependencies:
                parent_id = dependency.get(
                    "parent_id"
                )

                weight = dependency.get(
                    "weight",
                    1.0,
                )

                if parent_id not in self.nodes:
                    raise ValueError(
                        f"Infrastructure node "
                        f"'{node_id}' depends on "
                        f"unknown node '{parent_id}'."
                    )

                weight = float(weight)

                if weight < 0:
                    raise ValueError(
                        f"Dependency weight cannot be "
                        f"negative: {node_id} -> {parent_id}"
                    )

                relationship = {
                    "parent_id": parent_id,
                    "weight": weight,
                }

                self.parents[node_id].append(
                    relationship
                )

                self.children[parent_id].append(
                    node_id
                )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> bool:
        """
        Validate that the dependency graph is acyclic.

        Returns:
            True when the graph is a valid DAG.

        Raises:
            ValueError if a dependency cycle exists.
        """

        indegree = {
            node_id: 0
            for node_id in self.nodes
        }

        for parent_id, children in (
            self.children.items()
        ):
            for child_id in children:
                indegree[child_id] += 1

        queue = deque(
            node_id
            for node_id, degree in indegree.items()
            if degree == 0
        )

        visited_count = 0

        while queue:
            node_id = queue.popleft()
            visited_count += 1

            for child_id in self.children[node_id]:
                indegree[child_id] -= 1

                if indegree[child_id] == 0:
                    queue.append(child_id)

        if visited_count != len(
            self.nodes
        ):
            raise ValueError(
                "Circular infrastructure dependency detected."
            )

        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_parents(
        self,
        node_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Return dependency relationships for a node.
        """

        self._require_node(node_id)

        return [
            dict(dependency)
            for dependency in self.parents[node_id]
        ]

    def get_children(
        self,
        node_id: str,
    ) -> List[str]:
        """
        Return nodes that depend on the supplied node.
        """

        self._require_node(node_id)

        return list(
            self.children[node_id]
        )

    def get_root_nodes(self) -> List[str]:
        """
        Return infrastructure nodes that do not depend on another node.
        """

        return [
            node_id
            for node_id in self.nodes
            if not self.parents[node_id]
        ]

    def get_leaf_nodes(self) -> List[str]:
        """
        Return infrastructure nodes that have no dependents.
        """

        return [
            node_id
            for node_id in self.nodes
            if not self.children[node_id]
        ]

    def get_node(
        self,
        node_id: str,
    ) -> Dict[str, Any]:
        """
        Return a copy of a node's static metadata.
        """

        self._require_node(node_id)

        return dict(
            self.nodes[node_id]
        )

    def get_node_ids(self) -> List[str]:
        """
        Return all infrastructure node IDs.
        """

        return list(
            self.nodes.keys()
        )

    def topological_order(self) -> List[str]:
        """
        Return infrastructure nodes in dependency order.

        Parents appear before their dependent children.
        """

        indegree = {
            node_id: len(
                self.parents[node_id]
            )
            for node_id in self.nodes
        }

        queue = deque(
            node_id
            for node_id, degree in indegree.items()
            if degree == 0
        )

        order: List[str] = []

        while queue:
            node_id = queue.popleft()
            order.append(node_id)

            for child_id in self.children[node_id]:
                indegree[child_id] -= 1

                if indegree[child_id] == 0:
                    queue.append(child_id)

        if len(order) != len(
            self.nodes
        ):
            raise ValueError(
                "Cannot produce topological order "
                "because the dependency graph contains a cycle."
            )

        return order

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_node(
        self,
        node_id: str,
    ) -> None:
        if node_id not in self.nodes:
            raise KeyError(
                f"Unknown infrastructure node: {node_id}"
            )
