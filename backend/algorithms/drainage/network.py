from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


class NodeType(str, Enum):
    INLET = "INLET"
    JUNCTION = "JUNCTION"
    PUMP_STATION = "PUMP_STATION"
    OUTFALL = "OUTFALL"


@dataclass
class DrainageNode:
    """Represents a node in the stormwater drainage network."""
    id: str
    node_type: NodeType
    zone_id: str
    world_pos: dict[str, float]
    elevation_m: float
    invert_elevation_m: float
    inlet_capacity_m3_s: float = 0.0
    pump_capacity_m3_s: float = 0.0
    current_head: float = 0.0
    current_inflow: float = 0.0
    surcharged_flow: float = 0.0
    is_surcharging: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.node_type.value,
            "zone_id": self.zone_id,
            "world_pos": dict(self.world_pos),
            "elevation_m": self.elevation_m,
            "invert_elevation_m": self.invert_elevation_m,
            "inlet_capacity_m3_s": self.inlet_capacity_m3_s,
            "pump_capacity_m3_s": self.pump_capacity_m3_s,
            "current_head": self.current_head,
            "current_inflow": self.current_inflow,
            "surcharged_flow": self.surcharged_flow,
            "is_surcharging": self.is_surcharging,
        }


@dataclass
class DrainagePipe:
    """Represents a directed pipe / conduit edge in the drainage graph."""
    id: str
    from_node: str
    to_node: str
    diameter_m: float
    length_m: float
    slope: float
    roughness: float
    full_capacity_m3_s: float
    current_flow: float = 0.0
    utilization: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "from_node": self.from_node,
            "to_node": self.to_node,
            "diameter_m": self.diameter_m,
            "length_m": self.length_m,
            "slope": self.slope,
            "roughness": self.roughness,
            "full_capacity_m3_s": self.full_capacity_m3_s,
            "current_flow": self.current_flow,
            "utilization": self.utilization,
        }


class DrainageNetwork:
    """
    Authoritative topological graph for urban stormwater drainage.
    Manages nodes, pipes, zone associations, and flow capacities.
    """

    def __init__(
        self,
        nodes: Mapping[str, DrainageNode] | None = None,
        pipes: Mapping[str, DrainagePipe] | None = None,
    ) -> None:
        self.nodes: dict[str, DrainageNode] = dict(nodes) if nodes else {}
        self.pipes: dict[str, DrainagePipe] = dict(pipes) if pipes else {}

        self.pipes_by_source: dict[str, list[DrainagePipe]] = {}
        self.pipes_by_target: dict[str, list[DrainagePipe]] = {}
        self.zone_to_inlets: dict[str, list[str]] = {}

        self._rebuild_indices()

    def _rebuild_indices(self) -> None:
        self.pipes_by_source = {nid: [] for nid in self.nodes}
        self.pipes_by_target = {nid: [] for nid in self.nodes}
        self.zone_to_inlets = {}

        for node in self.nodes.values():
            if node.node_type == NodeType.INLET:
                self.zone_to_inlets.setdefault(node.zone_id, []).append(node.id)

        for pipe in self.pipes.values():
            if pipe.from_node in self.pipes_by_source:
                self.pipes_by_source[pipe.from_node].append(pipe)
            if pipe.to_node in self.pipes_by_target:
                self.pipes_by_target[pipe.to_node].append(pipe)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DrainageNetwork:
        nodes = {}
        for nid, n_data in data.get("nodes", {}).items():
            nodes[nid] = DrainageNode(
                id=n_data["id"],
                node_type=NodeType(n_data["type"]),
                zone_id=n_data.get("zone_id", ""),
                world_pos=n_data.get("world_pos", {"x": 0.0, "z": 0.0}),
                elevation_m=float(n_data.get("elevation_m", 10.0)),
                invert_elevation_m=float(n_data.get("invert_elevation_m", 8.0)),
                inlet_capacity_m3_s=float(n_data.get("inlet_capacity_m3_s", 0.0)),
                pump_capacity_m3_s=float(n_data.get("pump_capacity_m3_s", 0.0)),
            )

        pipes = {}
        for p_data in data.get("pipes", []):
            pid = p_data["id"]
            pipes[pid] = DrainagePipe(
                id=pid,
                from_node=p_data["from_node"],
                to_node=p_data["to_node"],
                diameter_m=float(p_data["diameter_m"]),
                length_m=float(p_data["length_m"]),
                slope=float(p_data["slope"]),
                roughness=float(p_data.get("roughness", 0.013)),
                full_capacity_m3_s=float(p_data["full_capacity_m3_s"]),
            )

        return cls(nodes=nodes, pipes=pipes)

    @classmethod
    def from_file(cls, path: str | Path) -> DrainageNetwork:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def get_inlets_for_zone(self, zone_id: str) -> list[DrainageNode]:
        inlet_ids = self.zone_to_inlets.get(zone_id, [])
        return [self.nodes[iid] for iid in inlet_ids if iid in self.nodes]

    def get_total_inlet_capacity(self, zone_id: str) -> float:
        inlets = self.get_inlets_for_zone(zone_id)
        return sum(i.inlet_capacity_m3_s for i in inlets)

    def get_pipes_from(self, node_id: str) -> list[DrainagePipe]:
        return self.pipes_by_source.get(node_id, [])

    def get_pipes_to(self, node_id: str) -> list[DrainagePipe]:
        return self.pipes_by_target.get(node_id, [])

    def reset_state(self) -> None:
        for node in self.nodes.values():
            node.current_head = 0.0
            node.current_inflow = 0.0
            node.surcharged_flow = 0.0
            node.is_surcharging = False

        for pipe in self.pipes.values():
            pipe.current_flow = 0.0
            pipe.utilization = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count": len(self.nodes),
            "pipe_count": len(self.pipes),
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "pipes": [p.to_dict() for p in self.pipes.values()],
        }
