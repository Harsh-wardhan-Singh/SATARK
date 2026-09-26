from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Mapping

from algorithms.drainage.hydraulics import ManningHydraulicsEngine
from algorithms.drainage.network import DrainageNetwork, NodeType

logger = logging.getLogger(__name__)


@dataclass
class ZoneDrainageSummary:
    """Summary of dual-layer surface-drainage exchange for a single zone."""
    zone_id: str
    surface_intake_rate: float = 0.0
    surcharge_rate: float = 0.0
    net_drainage_rate: float = 0.0
    pipe_utilization: float = 0.0
    is_surcharging: bool = False
    drainage_weakness: float = 0.0


@dataclass
class DrainageStepResult:
    """Complete output of one coupled drainage model simulation step."""
    zone_summaries: dict[str, ZoneDrainageSummary] = field(default_factory=dict)
    total_intake_flow: float = 0.0
    total_conveyed_flow: float = 0.0
    total_surcharge_flow: float = 0.0
    max_pipe_utilization: float = 0.0
    avg_pipe_utilization: float = 0.0
    active_pump_boosts: dict[str, float] = field(default_factory=dict)


class CoupledDrainageModel:
    """
    Simulates the dual-layer hydrodynamic exchange between surface stormwater
    and the underground pipe drainage network.

    1. Surface water drains into zone catch basins up to inlet capacity.
    2. Water propagates through pipes based on Manning hydraulics.
    3. When pipe/junction capacity is exceeded, surcharge flows back to the surface.
    4. Active pump interventions boost throughput at target pump stations.
    """

    # Representative zone catchment area (m^2) for depth-volume conversions
    DEFAULT_ZONE_AREA_M2: float = 10000.0

    def __init__(
        self,
        network: DrainageNetwork,
        zone_areas: Mapping[str, float] | None = None,
    ) -> None:
        self.network = network
        self.zone_areas: dict[str, float] = (
            dict(zone_areas) if zone_areas else {}
        )

    def step(
        self,
        water_levels: Mapping[str, float],
        delta_time: float,
        pump_boosts: Mapping[str, float] | None = None,
        global_pump_boost: float = 0.0,
    ) -> DrainageStepResult:
        """
        Advance the coupled drainage model by delta_time.

        Args:
            water_levels: Dict mapping zone_id -> current surface water depth (m).
            delta_time: Tick duration in seconds.
            pump_boosts: Dict mapping zone_id or pump_id -> additional discharge (m3/s).
            global_pump_boost: Global pump intervention rate boost.

        Returns:
            DrainageStepResult containing per-zone net rates and network metrics.
        """
        if delta_time <= 0.0:
            delta_time = 1.0

        self.network.reset_state()
        boosts_by_zone = dict(pump_boosts) if pump_boosts else {}

        node_inflows: dict[str, float] = {nid: 0.0 for nid in self.network.nodes}
        zone_summaries: dict[str, ZoneDrainageSummary] = {}

        # 1. Surface Intake: compute how much water can enter each zone's catch basins
        total_intake = 0.0
        for zone_id, depth in water_levels.items():
            if depth <= 0.0:
                continue

            inlets = self.network.get_inlets_for_zone(zone_id)
            if not inlets:
                continue

            area = self.zone_areas.get(zone_id, self.DEFAULT_ZONE_AREA_M2)
            surface_vol_available = depth * area
            max_vol_rate = surface_vol_available / delta_time

            total_inlet_cap = sum(i.inlet_capacity_m3_s for i in inlets)
            # Intake flow in m3/s
            actual_intake = min(max_vol_rate, total_inlet_cap)
            total_intake += actual_intake

            # Distribute intake among inlets for this zone
            if total_inlet_cap > 0.0:
                for inlet in inlets:
                    ratio = inlet.inlet_capacity_m3_s / total_inlet_cap
                    inlet_flow = actual_intake * ratio
                    node_inflows[inlet.id] += inlet_flow
                    inlet.current_inflow += inlet_flow

        # 2. Hydraulic propagation & surcharge evaluation through pipes
        # We sort pipes topologically (from highest invert elevation to lowest)
        sorted_pipes = sorted(
            self.network.pipes.values(),
            key=lambda p: self.network.nodes[p.from_node].invert_elevation_m,
            reverse=True,
        )

        total_conveyed = 0.0
        total_surcharge = 0.0
        pipe_utilizations: list[float] = []

        for pipe in sorted_pipes:
            from_node = self.network.nodes[pipe.from_node]
            to_node = self.network.nodes[pipe.to_node]

            # Inflow to this pipe is the accumulated inflow at from_node
            pipe_inflow = node_inflows.get(from_node.id, 0.0)

            # Check for pump boost if from_node is a pump station or zone has pump boost
            pump_boost = 0.0
            if from_node.node_type == NodeType.PUMP_STATION:
                pump_boost += from_node.pump_capacity_m3_s
                pump_boost += boosts_by_zone.get(from_node.zone_id, 0.0)
                pump_boost += boosts_by_zone.get(from_node.id, 0.0)
                pump_boost += global_pump_boost

            flow_res = ManningHydraulicsEngine.evaluate_pipe_flow(
                inflow_m3_s=pipe_inflow,
                capacity_m3_s=pipe.full_capacity_m3_s,
                pump_boost_m3_s=pump_boost,
            )

            pipe.current_flow = flow_res.conveyed_flow
            pipe.utilization = flow_res.utilization
            pipe_utilizations.append(flow_res.utilization)

            total_conveyed += flow_res.conveyed_flow

            # Surcharge excess stays at the upstream node
            if flow_res.is_surcharging:
                from_node.surcharged_flow += flow_res.surcharge_flow
                from_node.is_surcharging = True
                total_surcharge += flow_res.surcharge_flow

            # Conveyed flow is passed downstream to to_node
            if to_node.node_type != NodeType.OUTFALL:
                node_inflows[to_node.id] += flow_res.conveyed_flow
                to_node.current_inflow += flow_res.conveyed_flow

        # 3. Aggregate per-zone metrics
        for zone_id in self.network.zone_to_inlets:
            inlets = self.network.get_inlets_for_zone(zone_id)
            area = self.zone_areas.get(zone_id, self.DEFAULT_ZONE_AREA_M2)

            zone_intake_m3_s = sum(i.current_inflow for i in inlets)
            zone_surcharge_m3_s = sum(i.surcharged_flow for i in inlets)

            # Net drainage in m/s (depth equivalent)
            net_vol_rate = max(0.0, zone_intake_m3_s - zone_surcharge_m3_s)
            net_depth_rate = net_vol_rate / area

            # Maximum pipe utilization connected to zone inlets
            zone_pipes = [
                p for i in inlets for p in self.network.get_pipes_from(i.id)
            ]
            max_util = max((p.utilization for p in zone_pipes), default=0.0)

            # Drainage weakness in [0.0, 1.0] (higher means weaker/surcharging)
            if zone_intake_m3_s > 0:
                surcharge_ratio = min(1.0, zone_surcharge_m3_s / zone_intake_m3_s)
                weakness = 0.5 * max_util + 0.5 * surcharge_ratio
            else:
                weakness = 0.2  # baseline dry weakness

            zone_summaries[zone_id] = ZoneDrainageSummary(
                zone_id=zone_id,
                surface_intake_rate=zone_intake_m3_s,
                surcharge_rate=zone_surcharge_m3_s,
                net_drainage_rate=net_depth_rate,
                pipe_utilization=max_util,
                is_surcharging=zone_surcharge_m3_s > 1e-6,
                drainage_weakness=min(1.0, max(0.0, weakness)),
            )

        avg_util = (
            sum(pipe_utilizations) / len(pipe_utilizations)
            if pipe_utilizations
            else 0.0
        )
        max_util = max(pipe_utilizations, default=0.0)

        return DrainageStepResult(
            zone_summaries=zone_summaries,
            total_intake_flow=total_intake,
            total_conveyed_flow=total_conveyed,
            total_surcharge_flow=total_surcharge,
            max_pipe_utilization=max_util,
            avg_pipe_utilization=avg_util,
            active_pump_boosts=boosts_by_zone,
        )
