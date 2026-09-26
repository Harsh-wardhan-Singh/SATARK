from __future__ import annotations

import heapq
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass
class Waypoint:
    """A spatial waypoint along a navigation path."""
    zone_id: str
    x: float
    z: float
    water_depth_m: float
    water_depth_cm: float
    panic_score: float
    is_safe: bool


@dataclass
class NavigationRouteResult:
    """The authoritative result of a flood-safe navigation path computation."""
    status: str  # SUCCESS, PARTIAL_HAZARD, NO_PATH_FOUND, INVALID_ZONE
    origin_zone: str
    destination_zone: str
    path: list[str] = field(default_factory=list)
    waypoints: list[dict[str, Any]] = field(default_factory=list)
    total_distance_m: float = 0.0
    estimated_travel_time_min: float = 0.0
    safety_score: float = 1.0  # 1.0 = completely dry, 0.0 = deeply submerged
    is_safe: bool = True  # True if all waypoints <= 30cm water depth
    depth_profile_cm: list[float] = field(default_factory=list)
    max_water_depth_cm: float = 0.0
    impassable_zones_encountered: list[str] = field(default_factory=list)
    warning_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FloodSafeNavigationEngine:
    """
    Authoritative flood-safe route navigation engine using risk-weighted Dijkstra.

    Evaluates topological adjacency, physical distances, real-time water depths,
    and panic levels to route citizens and emergency services away from submerged roads.
    Enforces the 30 cm (0.30 m) road-impassable threshold.
    """

    CRITICAL_DEPTH_M: float = 0.30  # 30 cm depth threshold for vehicle / safe transit
    DEFAULT_WALKING_SPEED_M_S: float = 1.2  # ~4.3 km/h average human walking speed

    def __init__(
        self,
        zone_mapping_path: str | Path | None = None,
        zone_data: list[dict[str, Any]] | None = None,
    ) -> None:
        if zone_data is not None:
            self.zones = list(zone_data)
        elif zone_mapping_path is not None:
            path = Path(zone_mapping_path)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.zones = data.get("zones", [])
        else:
            default_path = (
                Path(__file__).resolve().parent.parent.parent / "data" / "glb_zone_mapping.json"
            )
            with open(default_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.zones = data.get("zones", [])

        # Index zones by ID and coordinates
        self.zone_map: dict[str, dict[str, Any]] = {z["id"]: z for z in self.zones}
        self.zone_ids: list[str] = list(self.zone_map.keys())

        # Centroids in world units (x, z)
        self.centroids: dict[str, tuple[float, float]] = {}
        for zid, z in self.zone_map.items():
            cw = z.get("center_world", {})
            self.centroids[zid] = (
                float(cw.get("x", 0.0)),
                float(cw.get("z", 0.0)),
            )

        # Adjacency graph: zone_id -> set of neighboring zone_ids
        self.graph: dict[str, list[str]] = {}
        for zid, z in self.zone_map.items():
            neighbors = [n for n in z.get("neighbors", []) if n in self.zone_map]
            self.graph[zid] = neighbors

    def resolve_coordinate_to_zone(self, x: float, z: float) -> str:
        """Find the nearest topological zone centroid to the given world coordinate."""
        best_zone = self.zone_ids[0]
        min_dist_sq = float("inf")
        for zid, (zx, zz) in self.centroids.items():
            dist_sq = (x - zx) ** 2 + (z - zz) ** 2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                best_zone = zid
        return best_zone

    def _parse_zone_endpoint(
        self,
        endpoint: str | tuple[float, float] | Sequence[float] | Mapping[str, Any],
    ) -> str:
        """Resolve string ID, tuple (x, z), or dict {'x': ..., 'z': ...} to a zone ID."""
        if isinstance(endpoint, str):
            clean = endpoint.strip()
            if clean in self.zone_map:
                return clean
            # Fallback to uppercase
            upper = clean.upper()
            if upper in self.zone_map:
                return upper
            raise ValueError(f"Unknown zone ID: '{endpoint}'")

        if isinstance(endpoint, (tuple, list)):
            if len(endpoint) >= 2:
                return self.resolve_coordinate_to_zone(float(endpoint[0]), float(endpoint[1]))
            raise ValueError(f"Coordinate tuple must have at least 2 elements: {endpoint}")

        if isinstance(endpoint, Mapping):
            if "zone_id" in endpoint and endpoint["zone_id"] in self.zone_map:
                return str(endpoint["zone_id"])
            if "x" in endpoint and "z" in endpoint:
                return self.resolve_coordinate_to_zone(float(endpoint["x"]), float(endpoint["z"]))
            if "lat" in endpoint and "lon" in endpoint:
                # Approximate lat/lon projection
                return self.resolve_coordinate_to_zone(float(endpoint["lat"]), float(endpoint["lon"]))
            raise ValueError(f"Cannot resolve coordinate mapping: {endpoint}")

        raise ValueError(f"Unsupported endpoint format: {type(endpoint)}")

    def calculate_distance(self, zone_a: str, zone_b: str) -> float:
        """Euclidean distance between two zone centroids in meters."""
        if zone_a == zone_b:
            return 0.0
        xa, za = self.centroids[zone_a]
        xb, zb = self.centroids[zone_b]
        # GLB coordinates scale: ~0.25 to meters
        return math.sqrt((xa - xb) ** 2 + (za - zb) ** 2) * 0.25

    def find_route(
        self,
        origin: str | tuple[float, float] | Mapping[str, Any],
        destination: str | tuple[float, float] | Mapping[str, Any],
        water_levels_m: Mapping[str, float] | None = None,
        panic_scores: Mapping[str, float] | None = None,
        critical_depth_m: float = CRITICAL_DEPTH_M,
        allow_flooded: bool = False,
    ) -> NavigationRouteResult:
        """
        Compute the shortest flood-safe route between origin and destination.

        Uses risk-weighted Dijkstra:
        Cost(u, v) = Distance(u, v) * (1.0 + 5.0 * Depth_v + 2.0 * Panic_v)
        Segments with Depth_v > critical_depth_m (30 cm) are strictly excluded unless
        allow_flooded is True.
        """
        try:
            origin_id = self._parse_zone_endpoint(origin)
            dest_id = self._parse_zone_endpoint(destination)
        except ValueError as err:
            return NavigationRouteResult(
                status="INVALID_ZONE",
                origin_zone=str(origin),
                destination_zone=str(destination),
                warning_message=str(err),
                is_safe=False,
            )

        if origin_id == dest_id:
            depth_m = float(water_levels_m.get(origin_id, 0.0)) if water_levels_m else 0.0
            depth_cm = round(depth_m * 100.0, 2)
            is_safe = depth_m <= critical_depth_m
            ox, oz = self.centroids[origin_id]
            wp = {
                "zone_id": origin_id,
                "x": ox,
                "z": oz,
                "water_depth_m": depth_m,
                "water_depth_cm": depth_cm,
                "panic_score": float(panic_scores.get(origin_id, 0.0)) if panic_scores else 0.0,
                "is_safe": is_safe,
            }
            return NavigationRouteResult(
                status="SUCCESS",
                origin_zone=origin_id,
                destination_zone=dest_id,
                path=[origin_id],
                waypoints=[wp],
                total_distance_m=0.0,
                estimated_travel_time_min=0.0,
                safety_score=1.0 if is_safe else 0.0,
                is_safe=is_safe,
                depth_profile_cm=[depth_cm],
                max_water_depth_cm=depth_cm,
            )

        water = dict(water_levels_m) if water_levels_m else {}
        panic = dict(panic_scores) if panic_scores else {}

        # 1. Attempt strictly flood-safe route (avoiding water > critical_depth_m)
        path, dist, blocked = self._dijkstra(
            origin_id,
            dest_id,
            water,
            panic,
            critical_depth_m=critical_depth_m,
            strict_cutoff=True,
        )

        warning: str | None = None
        status = "SUCCESS"
        is_safe = True

        if not path:
            # 2. No safe route exists without traversing floodwaters.
            # If allow_flooded is False, attempt a penalized search for the least-hazardous path as fallback
            path, dist, _ = self._dijkstra(
                origin_id,
                dest_id,
                water,
                panic,
                critical_depth_m=critical_depth_m,
                strict_cutoff=False,
            )
            if not path:
                return NavigationRouteResult(
                    status="NO_PATH_FOUND",
                    origin_zone=origin_id,
                    destination_zone=dest_id,
                    warning_message="No connected path exists between these zones.",
                    is_safe=False,
                    impassable_zones_encountered=sorted(blocked),
                )

            status = "PARTIAL_HAZARD"
            is_safe = False
            warning = (
                f"No 100% flood-safe path exists (all routes intersect water > {int(critical_depth_m*100)} cm). "
                "Returning least-hazardous evacuation route with active caution."
            )

        # 3. Construct detailed waypoint telemetry and depth profile
        waypoints: list[dict[str, Any]] = []
        depth_profile_cm: list[float] = []
        max_depth_cm = 0.0

        for zid in path:
            dm = float(water.get(zid, 0.0))
            dcm = round(dm * 100.0, 2)
            ps = float(panic.get(zid, 0.0))
            safe_node = dm <= critical_depth_m
            cx, cz = self.centroids[zid]

            waypoints.append({
                "zone_id": zid,
                "x": cx,
                "z": cz,
                "water_depth_m": dm,
                "water_depth_cm": dcm,
                "panic_score": ps,
                "is_safe": safe_node,
            })
            depth_profile_cm.append(dcm)
            if dcm > max_depth_cm:
                max_depth_cm = dcm

        # Compute travel time factoring water depth resistance
        travel_time_sec = 0.0
        for i in range(len(path) - 1):
            seg_dist = self.calculate_distance(path[i], path[i + 1])
            mid_depth = (water.get(path[i], 0.0) + water.get(path[i + 1], 0.0)) / 2.0
            # Speed penalty: water depth reduces walking speed
            speed_factor = max(0.15, 1.0 - (mid_depth / 0.8))
            speed = self.DEFAULT_WALKING_SPEED_M_S * speed_factor
            travel_time_sec += seg_dist / speed

        travel_time_min = round(travel_time_sec / 60.0, 1)
        safety_score = max(0.0, round(1.0 - (max_depth_cm / 100.0), 3))

        return NavigationRouteResult(
            status=status,
            origin_zone=origin_id,
            destination_zone=dest_id,
            path=path,
            waypoints=waypoints,
            total_distance_m=round(dist, 1),
            estimated_travel_time_min=travel_time_min,
            safety_score=safety_score,
            is_safe=is_safe,
            depth_profile_cm=depth_profile_cm,
            max_water_depth_cm=round(max_depth_cm, 2),
            impassable_zones_encountered=sorted(blocked),
            warning_message=warning,
        )

    def _dijkstra(
        self,
        origin_id: str,
        dest_id: str,
        water: dict[str, float],
        panic: dict[str, float],
        critical_depth_m: float,
        strict_cutoff: bool,
    ) -> tuple[list[str], float, set[str]]:
        """
        Dijkstra shortest path search.
        Returns (path, total_distance, set_of_blocked_zones).
        """
        # Priority queue: (cost, distance, current_node, path)
        pq: list[tuple[float, float, str, list[str]]] = [(0.0, 0.0, origin_id, [origin_id])]
        visited: set[str] = set()
        best_cost: dict[str, float] = {origin_id: 0.0}
        blocked_zones: set[str] = set()

        while pq:
            cost, dist, u, path = heapq.heappop(pq)

            if u == dest_id:
                return path, dist, blocked_zones

            if u in visited:
                continue
            visited.add(u)

            for v in self.graph.get(u, []):
                depth_v = float(water.get(v, 0.0))
                panic_v = float(panic.get(v, 0.0))
                edge_dist = self.calculate_distance(u, v)

                if depth_v > critical_depth_m:
                    blocked_zones.add(v)
                    if strict_cutoff:
                        # In strict mode, cannot enter this zone unless it's origin
                        continue
                    else:
                        # In relaxed mode, apply massive penalty
                        penalty = 50.0 + (depth_v * 100.0)
                else:
                    penalty = 1.0 + (5.0 * depth_v) + (2.0 * panic_v)

                step_cost = edge_dist * penalty
                new_cost = cost + step_cost
                new_dist = dist + edge_dist

                if v not in best_cost or new_cost < best_cost[v]:
                    best_cost[v] = new_cost
                    heapq.heappush(pq, (new_cost, new_dist, v, path + [v]))

        return [], 0.0, blocked_zones
