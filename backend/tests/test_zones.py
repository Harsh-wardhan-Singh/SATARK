"""
Test suite for GLB zone data validation.

Tests the structural integrity and relationships of zone data in
data/glb_zone_mapping.json, including coordinates, neighbor relationships,
and spatial resolution.
"""

import json
import sys
from pathlib import Path


# Load zone data once for all tests
def load_zone_data():
    """Load the zone data from JSON file."""
    data_file = Path(__file__).parent.parent / "data" / "glb_zone_mapping.json"
    with open(data_file, 'r') as f:
        return json.load(f)


ZONE_DATA = load_zone_data()
ZONES = ZONE_DATA["zones"]
ZONES_BY_ID = {zone["id"]: zone for zone in ZONES}


def get_nearest_zone(x: float, z: float) -> str:
    """
    Find the zone whose center_world is closest to the given coordinates.
    
    Uses squared Euclidean distance:
        distance_squared = (x - center_x)^2 + (z - center_z)^2
    
    Args:
        x: World X coordinate
        z: World Z coordinate
    
    Returns:
        Zone ID of the closest zone
    """
    min_distance_sq = float('inf')
    nearest_zone_id = None
    
    for zone in ZONES:
        center_x = zone["center_world"]["x"]
        center_z = zone["center_world"]["z"]
        distance_sq = (x - center_x) ** 2 + (z - center_z) ** 2
        
        if distance_sq < min_distance_sq:
            min_distance_sq = distance_sq
            nearest_zone_id = zone["id"]
    
    return nearest_zone_id


# Test 1: Exactly 21 zones exist
def test_zone_count():
    """Test that exactly 21 zones exist."""
    assert len(ZONES) == 21, f"Expected 21 zones, got {len(ZONES)}"


# Test 2: Zone IDs are exactly Z01 through Z21
def test_zone_ids():
    """Test that zone IDs are Z01, Z02, ..., Z21."""
    expected_ids = {f"Z{i:02d}" for i in range(1, 22)}
    actual_ids = {zone["id"] for zone in ZONES}
    assert actual_ids == expected_ids, f"Zone IDs mismatch. Expected {sorted(expected_ids)}, got {sorted(actual_ids)}"


# Test 3: Zone IDs are unique
def test_zone_ids_unique():
    """Test that zone IDs are unique."""
    zone_ids = [zone["id"] for zone in ZONES]
    assert len(zone_ids) == len(set(zone_ids)), "Duplicate zone IDs found"


# Test 4: Every zone has center_world.x and center_world.z
def test_world_coordinates_exist():
    """Test that every zone has center_world.x and center_world.z."""
    for zone in ZONES:
        zone_id = zone["id"]
        assert "center_world" in zone, f"Zone {zone_id} missing center_world"
        assert "x" in zone["center_world"], f"Zone {zone_id} center_world missing x"
        assert "z" in zone["center_world"], f"Zone {zone_id} center_world missing z"
        
        # Also verify they are numeric
        try:
            float(zone["center_world"]["x"])
            float(zone["center_world"]["z"])
        except (TypeError, ValueError):
            raise AssertionError(f"Zone {zone_id} center_world x or z is not numeric")


# Test 5: Every zone has center_normalized.x and center_normalized.y
def test_normalized_coordinates_exist():
    """Test that every zone has center_normalized.x and center_normalized.y."""
    for zone in ZONES:
        zone_id = zone["id"]
        assert "center_normalized" in zone, f"Zone {zone_id} missing center_normalized"
        assert "x" in zone["center_normalized"], f"Zone {zone_id} center_normalized missing x"
        assert "y" in zone["center_normalized"], f"Zone {zone_id} center_normalized missing y"
        
        # Also verify they are numeric
        try:
            float(zone["center_normalized"]["x"])
            float(zone["center_normalized"]["y"])
        except (TypeError, ValueError):
            raise AssertionError(f"Zone {zone_id} center_normalized x or y is not numeric")


# Test 6: Every normalized coordinate is between 0 and 1
def test_normalized_coordinates_range():
    """Test that every normalized coordinate is between 0 and 1."""
    for zone in ZONES:
        zone_id = zone["id"]
        x = float(zone["center_normalized"]["x"])
        y = float(zone["center_normalized"]["y"])
        
        assert 0 <= x <= 1, f"Zone {zone_id} center_normalized.x = {x} is not in [0, 1]"
        assert 0 <= y <= 1, f"Zone {zone_id} center_normalized.y = {y} is not in [0, 1]"


# Test 7: Every neighbor exists
def test_neighbor_references():
    """Test that every neighbor references an existing zone."""
    for zone in ZONES:
        zone_id = zone["id"]
        neighbors = zone.get("neighbors", [])
        
        for neighbor_id in neighbors:
            assert neighbor_id in ZONES_BY_ID, \
                f"Zone {zone_id} references non-existent neighbor {neighbor_id}"


# Test 8: No zone is its own neighbor
def test_no_self_neighbors():
    """Test that no zone is its own neighbor."""
    for zone in ZONES:
        zone_id = zone["id"]
        neighbors = zone.get("neighbors", [])
        
        assert zone_id not in neighbors, \
            f"Zone {zone_id} contains itself as a neighbor"


# Test 9: Neighbor relationships are symmetric
def test_neighbor_symmetry():
    """Test that neighbor relationships are symmetric (bidirectional)."""
    for zone in ZONES:
        zone_id = zone["id"]
        neighbors = zone.get("neighbors", [])
        
        for neighbor_id in neighbors:
            neighbor_zone = ZONES_BY_ID[neighbor_id]
            neighbor_neighbors = neighbor_zone.get("neighbors", [])
            
            assert zone_id in neighbor_neighbors, \
                f"Zone {zone_id} lists {neighbor_id} as neighbor, but {neighbor_id} does not list {zone_id}"


# Test 10: Every zone has at least one neighbor
def test_zone_has_neighbors():
    """Test that every zone has at least one neighbor."""
    for zone in ZONES:
        zone_id = zone["id"]
        neighbors = zone.get("neighbors", [])
        
        assert len(neighbors) > 0, f"Zone {zone_id} has no neighbors"


# Test 11: Every zone's center resolves to itself
def test_nearest_zone_resolution():
    """Test that get_nearest_zone returns the zone itself when called with its center.
    
    This critical test verifies that the spatial index works correctly:
    when queried at a zone's center_world coordinates, the function must
    return that zone's ID.
    """
    for zone in ZONES:
        zone_id = zone["id"]
        center_x = zone["center_world"]["x"]
        center_z = zone["center_world"]["z"]
        
        nearest = get_nearest_zone(center_x, center_z)
        assert nearest == zone_id, \
            f"get_nearest_zone({center_x}, {center_z}) returned {nearest}, expected {zone_id}"


if __name__ == "__main__":
    # Run all test functions
    test_functions = [
        ("test_zone_count", test_zone_count),
        ("test_zone_ids", test_zone_ids),
        ("test_zone_ids_unique", test_zone_ids_unique),
        ("test_world_coordinates_exist", test_world_coordinates_exist),
        ("test_normalized_coordinates_exist", test_normalized_coordinates_exist),
        ("test_normalized_coordinates_range", test_normalized_coordinates_range),
        ("test_neighbor_references", test_neighbor_references),
        ("test_no_self_neighbors", test_no_self_neighbors),
        ("test_neighbor_symmetry", test_neighbor_symmetry),
        ("test_zone_has_neighbors", test_zone_has_neighbors),
        ("test_nearest_zone_resolution", test_nearest_zone_resolution),
    ]
    
    passed = 0
    failed = 0
    
    print("=" * 60)
    print("ZONE DATA TESTS")
    print("=" * 60)
    print()
    
    for test_name, test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_name}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_name}")
            print(f"  Unexpected error: {e}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    sys.exit(0 if failed == 0 else 1)
