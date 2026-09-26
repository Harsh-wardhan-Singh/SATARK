import json
import tempfile
from pathlib import Path
import pytest
from algorithms.population.panic import PanicEngine
from algorithms.population.evacuation import EvacuationEngine

def test_panic_engine_escalation_and_decay():
    pop_data = {
        "zones": [
            {
                "zone_id": "Z01",
                "resident_population_estimate": 1000,
                "population_weight": 0.5
            },
            {
                "zone_id": "Z02",
                "resident_population_estimate": 200,
                "population_weight": 0.1
            }
        ]
    }
    engine = PanicEngine(pop_data)
    assert engine.panic_state["Z01"] == 0.0
    assert engine.panic_state["Z02"] == 0.0
    
    # Severe flood in Z01, no flood in Z02
    flood_impacts = {"Z01": 0.8, "Z02": 0.0}
    infra_states = {
        "node_1": {"zone_id": "Z01", "capacity": 0.1},
        "node_2": {"zone_id": "Z02", "capacity": 1.0}
    }
    
    new_panic = engine.update_panic(flood_impacts, infra_states)
    assert new_panic["Z01"] > 0.0
    # Z01 panic should be higher than Z02
    assert new_panic["Z01"] > new_panic["Z02"]
    
    # Now flood recedes and infra recovers -> panic decays
    decayed_panic = engine.update_panic({"Z01": 0.0, "Z02": 0.0}, {
        "node_1": {"zone_id": "Z01", "capacity": 1.0},
        "node_2": {"zone_id": "Z02", "capacity": 1.0}
    })
    assert decayed_panic["Z01"] < new_panic["Z01"]

def test_evacuation_engine_routing():
    zones_data = {
        "zones": [
            {"id": "Z01", "neighbors": ["Z02"]},
            {"id": "Z02", "neighbors": ["Z01", "Z03"]},
            {"id": "Z03", "neighbors": ["Z02"]}
        ]
    }
    shelters_data = {
        "shelters": [
            {"id": "S01", "zone_id": "Z03", "capacity": 1000}
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as fz:
        json.dump(zones_data, fz)
        zones_file = fz.name
        
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as fs:
        json.dump(shelters_data, fs)
        shelters_file = fs.name
        
    try:
        evac_engine = EvacuationEngine(zones_file, shelters_file)
        
        # Scenario 1: Shelter in Z03 is safe (water 0.0)
        flood_states = {"Z01": 0.1, "Z02": 0.1, "Z03": 0.0}
        panic_states = {"Z01": 0.2, "Z02": 0.2, "Z03": 0.1}
        
        routes = evac_engine.calculate_evacuation_routes(flood_states, panic_states)
        assert "Z01" in routes
        assert routes["Z01"]["safe"] is True
        # Path from Z01 should lead to Z03 through Z02
        assert routes["Z01"]["path"] == ["Z01", "Z02", "Z03"]
        
        # Scenario 2: Shelter compromised by heavy flood (> 0.4)
        flood_compromised = {"Z01": 0.1, "Z02": 0.1, "Z03": 0.8}
        crit_routes = evac_engine.calculate_evacuation_routes(flood_compromised, panic_states)
        assert crit_routes.get("status") == "CRITICAL"
    finally:
        Path(zones_file).unlink(missing_ok=True)
        Path(shelters_file).unlink(missing_ok=True)
