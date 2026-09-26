from __future__ import annotations

from pathlib import Path
import pytest
from rest_framework.test import APIClient

from algorithms.navigation.router import FloodSafeNavigationEngine, NavigationRouteResult
from core.enums import CalamityType
from core.types import SimulationConfig
from simulation.engine import SimulationEngine
from simulation.scenario import Scenario


@pytest.fixture
def zone_mapping_path() -> Path:
    p = Path(__file__).resolve().parent.parent / "data" / "glb_zone_mapping.json"
    assert p.exists(), f"Zone mapping file not found at {p}"
    return p


# ==============================================================================
# 1. Navigation Algorithm Tests
# ==============================================================================

def test_navigation_router_dry_conditions(zone_mapping_path: Path) -> None:
    router = FloodSafeNavigationEngine(zone_mapping_path=zone_mapping_path)
    result = router.find_route(origin="Z01", destination="Z13")

    assert result.status == "SUCCESS"
    assert result.is_safe is True
    assert result.origin_zone == "Z01"
    assert result.destination_zone == "Z13"
    assert result.path[0] == "Z01"
    assert result.path[-1] == "Z13"
    assert len(result.path) >= 2

    # Every step in path must be a valid neighbor of the preceding step
    for i in range(len(result.path) - 1):
        u = result.path[i]
        v = result.path[i + 1]
        assert v in router.graph[u], f"Zone {v} is not adjacent to {u}!"

    assert len(result.waypoints) == len(result.path)
    assert result.total_distance_m > 0.0
    assert result.estimated_travel_time_min > 0.0
    assert result.safety_score == 1.0


def test_navigation_router_flood_avoidance(zone_mapping_path: Path) -> None:
    router = FloodSafeNavigationEngine(zone_mapping_path=zone_mapping_path)

    # First find baseline dry path between Z01 and Z10
    dry_result = router.find_route(origin="Z01", destination="Z10")
    assert dry_result.status == "SUCCESS"
    dry_path = list(dry_result.path)

    # Pick an intermediate zone on the dry path
    assert len(dry_path) >= 3
    blocked_zone = dry_path[1]

    # Submerge the intermediate zone with 0.50m (50 cm > 30 cm threshold)
    water_levels = {blocked_zone: 0.50}
    flooded_result = router.find_route(
        origin="Z01",
        destination="Z10",
        water_levels_m=water_levels,
    )

    # The router should have routed AROUND the blocked zone
    assert flooded_result.status in ("SUCCESS", "PARTIAL_HAZARD")
    assert blocked_zone not in flooded_result.path, (
        f"Router traversed flooded zone {blocked_zone} when detour was available! "
        f"Path: {flooded_result.path}"
    )
    assert blocked_zone in flooded_result.impassable_zones_encountered


def test_navigation_router_trapped_fallback(zone_mapping_path: Path) -> None:
    router = FloodSafeNavigationEngine(zone_mapping_path=zone_mapping_path)

    # Submerge ALL neighbors of Z01 deeply (1.0m water)
    neighbors = router.graph["Z01"]
    water_levels = {nid: 1.0 for nid in neighbors}

    # In strict mode, no completely safe path exists
    result = router.find_route(
        origin="Z01",
        destination="Z13",
        water_levels_m=water_levels,
    )

    # Router falls back to least-hazardous route and alerts operator
    assert result.status == "PARTIAL_HAZARD"
    assert result.is_safe is False
    assert result.warning_message is not None
    assert len(result.path) >= 2


def test_coordinate_resolution(zone_mapping_path: Path) -> None:
    router = FloodSafeNavigationEngine(zone_mapping_path=zone_mapping_path)

    # Exact centroid of Z01
    z01_centroid = router.centroids["Z01"]
    resolved = router.resolve_coordinate_to_zone(z01_centroid[0], z01_centroid[1])
    assert resolved == "Z01"

    # Route using coordinate dicts
    z10_centroid = router.centroids["Z10"]
    route = router.find_route(
        origin={"x": z01_centroid[0], "z": z01_centroid[1]},
        destination={"x": z10_centroid[0], "z": z10_centroid[1]},
    )
    assert route.status == "SUCCESS"
    assert route.origin_zone == "Z01"
    assert route.destination_zone == "Z10"


# ==============================================================================
# 2. REST API Endpoint Tests
# ==============================================================================

def test_world_zones_api_endpoint() -> None:
    client = APIClient()
    resp = client.get("/api/world/zones/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["count"] == 21
    assert len(data["zones"]) == 21
    zone_ids = [z["id"] for z in data["zones"]]
    assert "Z01" in zone_ids
    assert "Z21" in zone_ids


def test_world_shelters_api_endpoint() -> None:
    client = APIClient()
    resp = client.get("/api/world/shelters/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["count"] == 3
    assert len(data["shelters"]) == 3
    shelter_ids = [s["id"] for s in data["shelters"]]
    assert "S1" in shelter_ids
    assert "S2" in shelter_ids
    assert "S3" in shelter_ids
    for s in data["shelters"]:
        assert "zoneId" in s
        assert "capacity" in s
        assert s["capacity"] > 0


def test_world_bounds_api_endpoint() -> None:
    client = APIClient()
    resp = client.get("/api/world/bounds/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    bounds = data["bounds"]
    assert "x_min" in bounds
    assert "x_max" in bounds
    assert "z_min" in bounds
    assert "z_max" in bounds
    assert bounds["x_max"] > bounds["x_min"]
    assert bounds["z_max"] > bounds["z_min"]


def test_navigation_route_api_endpoint() -> None:
    client = APIClient()
    payload = {
        "origin_zone": "Z01",
        "destination_zone": "Z13",
        "allow_flooded": False,
    }
    resp = client.post("/api/navigation/route/", payload, format="json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["origin_zone"] == "Z01"
    assert data["destination_zone"] == "Z13"
    assert data["path"][0] == "Z01"
    assert data["path"][-1] == "Z13"
    assert len(data["waypoints"]) == len(data["path"])
    assert data["total_distance_m"] > 0.0


def test_navigation_route_api_invalid_input() -> None:
    client = APIClient()
    # Missing destination
    resp = client.post("/api/navigation/route/", {"origin_zone": "Z01"}, format="json")
    assert resp.status_code in (400, 422)

    # Invalid zone name
    resp_invalid = client.post(
        "/api/navigation/route/",
        {"origin_zone": "Z99_DOES_NOT_EXIST", "destination_zone": "Z01"},
        format="json",
    )
    assert resp_invalid.status_code == 200
    data = resp_invalid.json()
    assert data["status"] == "INVALID_ZONE"
