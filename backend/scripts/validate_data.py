#!/usr/bin/env python3
"""
Validate GLB zone data for the disaster simulation project.

Validates:
1. Top-level "zones" list exists
2. Exactly 21 zones
3. Each zone has required fields
4. Unique zone IDs in format Z01-Z21
5. Valid world and normalized coordinates
6. Valid neighbor references and symmetry
"""

import json
import sys
from pathlib import Path


def load_zone_data(filepath: str) -> dict | None:
    """Load and parse the zone JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[FAIL] Failed to load JSON file: {e}")
        return None


def validate_zones(data: dict) -> tuple[bool, list[str]]:
    """
    Validate all zone data according to requirements.
    
    Returns:
        (all_pass: bool, results: list of check results)
    """
    results = []
    
    # 1. Check for top-level "zones" list
    if "zones" not in data:
        results.append(("[FAIL] Zones list missing", False))
        return False, results
    
    zones = data["zones"]
    if not isinstance(zones, list):
        results.append(("[FAIL] 'zones' is not a list", False))
        return False, results
    
    # 2. Check zone count
    if len(zones) != 21:
        results.append((f"[FAIL] Zone count - Expected 21, got {len(zones)}", False))
        return False, results
    results.append(("[PASS] Zone count", True))
    
    # Extract zones by ID for later reference
    zones_by_id = {zone.get("id"): zone for zone in zones}
    
    # 3 & 4 & 5. Check IDs: unique, in correct format Z01-Z21
    expected_ids = {f"Z{i:02d}" for i in range(1, 22)}
    actual_ids = {zone.get("id") for zone in zones}
    
    if actual_ids != expected_ids:
        missing = expected_ids - actual_ids
        extra = actual_ids - expected_ids
        msg = "[FAIL] Zone IDs"
        if missing:
            msg += f" - Missing: {sorted(missing)}"
        if extra:
            msg += f" - Extra: {sorted(extra)}"
        results.append((msg, False))
        return False, results
    results.append(("[PASS] Zone IDs", True))
    results.append(("[PASS] Unique IDs", True))
    
    # 3. Check required fields in each zone
    required_fields = {"id", "center_world", "center_normalized", "neighbors"}
    for zone in zones:
        zone_id = zone.get("id")
        missing = required_fields - set(zone.keys())
        if missing:
            results.append((f"[FAIL] Zone {zone_id} missing fields: {missing}", False))
            return False, results
    
    # 6. Check world coordinates (numeric x and z)
    for zone in zones:
        zone_id = zone.get("id")
        center_world = zone.get("center_world", {})
        
        if not isinstance(center_world, dict):
            results.append((f"[FAIL] Zone {zone_id}: center_world is not a dict", False))
            return False, results
        
        if "x" not in center_world or "z" not in center_world:
            results.append((f"[FAIL] Zone {zone_id}: center_world missing x or z", False))
            return False, results
        
        try:
            float(center_world["x"])
            float(center_world["z"])
        except (TypeError, ValueError):
            results.append((f"[FAIL] Zone {zone_id}: center_world x or z not numeric", False))
            return False, results
    results.append(("[PASS] World coordinates", True))
    
    # 7 & 8. Check normalized coordinates (numeric x and y, between 0 and 1)
    for zone in zones:
        zone_id = zone.get("id")
        center_norm = zone.get("center_normalized", {})
        
        if not isinstance(center_norm, dict):
            results.append((f"[FAIL] Zone {zone_id}: center_normalized is not a dict", False))
            return False, results
        
        if "x" not in center_norm or "y" not in center_norm:
            results.append((f"[FAIL] Zone {zone_id}: center_normalized missing x or y", False))
            return False, results
        
        try:
            x = float(center_norm["x"])
            y = float(center_norm["y"])
            
            if not (0 <= x <= 1):
                results.append((f"[FAIL] Zone {zone_id}: normalized x={x} not in [0, 1]", False))
                return False, results
            if not (0 <= y <= 1):
                results.append((f"[FAIL] Zone {zone_id}: normalized y={y} not in [0, 1]", False))
                return False, results
        except (TypeError, ValueError):
            results.append((f"[FAIL] Zone {zone_id}: center_normalized x or y not numeric", False))
            return False, results
    results.append(("[PASS] Normalized coordinates", True))
    
    # 9. Check neighbor references (must exist)
    for zone in zones:
        zone_id = zone.get("id")
        neighbors = zone.get("neighbors", [])
        
        if not isinstance(neighbors, list):
            results.append((f"[FAIL] Zone {zone_id}: neighbors is not a list", False))
            return False, results
        
        for neighbor_id in neighbors:
            if neighbor_id not in zones_by_id:
                results.append((f"[FAIL] Zone {zone_id}: neighbor {neighbor_id} does not exist", False))
                return False, results
    results.append(("[PASS] Neighbor references", True))
    
    # 10. Check for self-references
    for zone in zones:
        zone_id = zone.get("id")
        neighbors = zone.get("neighbors", [])
        
        if zone_id in neighbors:
            results.append((f"[FAIL] Zone {zone_id}: self-reference detected", False))
            return False, results
    results.append(("[PASS] No self references", True))
    
    # 12. Check for duplicate neighbors
    for zone in zones:
        zone_id = zone.get("id")
        neighbors = zone.get("neighbors", [])
        
        if len(neighbors) != len(set(neighbors)):
            duplicates = [n for n in neighbors if neighbors.count(n) > 1]
            results.append((f"[FAIL] Zone {zone_id}: duplicate neighbors {set(duplicates)}", False))
            return False, results
    results.append(("[PASS] No duplicate neighbors", True))
    
    # 11. Check neighbor symmetry
    for zone in zones:
        zone_id = zone.get("id")
        neighbors = zone.get("neighbors", [])
        
        for neighbor_id in neighbors:
            neighbor_zone = zones_by_id[neighbor_id]
            neighbor_neighbors = neighbor_zone.get("neighbors", [])
            
            if zone_id not in neighbor_neighbors:
                results.append((f"[FAIL] Asymmetric relationship: {zone_id} -> {neighbor_id}, but {neighbor_id} does not list {zone_id}", False))
                return False, results
    results.append(("[PASS] Neighbor symmetry", True))
    
    return True, results


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    data_file = script_dir.parent / "data" / "glb_zone_mapping.json"
    
    print("=" * 40)
    print("       GLB ZONE DATA VALIDATION")
    print("=" * 40)
    print()
    
    # Load data
    data = load_zone_data(str(data_file))
    if data is None:
        sys.exit(1)
    
    # Get zone count for display
    zones_count = len(data.get("zones", []))
    print(f"Zones: {zones_count}")
    print()
    
    # Validate
    all_pass, results = validate_zones(data)
    
    # Print results
    for result_msg, _ in results:
        print(result_msg)
    
    print()
    print("=" * 40)
    if all_pass:
        print("RESULT: PASS")
        print("=" * 40)
        sys.exit(0)
    else:
        print("RESULT: FAIL")
        print("=" * 40)
        sys.exit(1)


if __name__ == "__main__":
    main()
