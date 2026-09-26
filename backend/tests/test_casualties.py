import pytest
from algorithms.casualties.estimation import CasualtiesEngine

def test_casualties_engine_initialization():
    infra_data = {
        "infrastructure": [
            {"id": "hosp-1", "type": "medical", "zone_id": "Z01"},
            {"id": "power-1", "type": "power", "zone_id": "Z02"},
        ]
    }
    engine = CasualtiesEngine(infra_data)
    assert len(engine.hospitals) == 1
    assert "hosp-1" in engine.hospitals
    assert engine.total_fatalities == 0
    assert engine.total_injuries == 0

def test_casualties_environmental_flood():
    infra_data = {
        "infrastructure": [
            {"id": "hosp-1", "type": "medical", "zone_id": "Z01"}
        ]
    }
    engine = CasualtiesEngine(infra_data)
    
    current_pops = {"Z01": 1000}
    flood_states = {"Z01": 0.8}
    bottlenecks = {"Z01": 0.5}
    panic_states = {"Z01": 0.2}
    infra_states = {"hosp-1": {"capacity": 1.0}}
    
    result = engine.update_casualties(
        current_populations=current_pops,
        flood_states=flood_states,
        bottlenecks=bottlenecks,
        panic_states=panic_states,
        infra_states=infra_states,
        time_step_seconds=3600.0,
    )
    
    assert result["total_injuries"] > 0
    assert result["total_fatalities"] > 0
    assert result["medical_system_health"] == 1.0
    assert "Z01" in result["zone_breakdown"]

def test_casualties_medical_system_failure_escalation():
    infra_data = {
        "infrastructure": [
            {"id": "hosp-1", "type": "medical", "zone_id": "Z01"}
        ]
    }
    # Hospital operational
    engine_healthy = CasualtiesEngine(infra_data)
    res_healthy = engine_healthy.update_casualties(
        current_populations={"Z01": 2000},
        flood_states={"Z01": 0.9},
        bottlenecks={"Z01": 0.5},
        panic_states={"Z01": 0.2},
        infra_states={"hosp-1": {"capacity": 1.0}},
        time_step_seconds=3600.0,
    )
    
    # Hospital collapsed
    engine_collapsed = CasualtiesEngine(infra_data)
    res_collapsed = engine_collapsed.update_casualties(
        current_populations={"Z01": 2000},
        flood_states={"Z01": 0.9},
        bottlenecks={"Z01": 0.5},
        panic_states={"Z01": 0.2},
        infra_states={"hosp-1": {"capacity": 0.0}},
        time_step_seconds=3600.0,
    )
    
    # When medical system collapses, triage failure converts injuries to fatalities
    assert res_collapsed["total_fatalities"] > res_healthy["total_fatalities"]
    assert res_collapsed["medical_system_health"] == 0.0

def test_casualties_stampede_vector():
    infra_data = {"infrastructure": []}
    engine = CasualtiesEngine(infra_data)
    
    # High congestion (bottleneck > 1.2) and high panic (> 0.5) with no flood
    res = engine.update_casualties(
        current_populations={"Z02": 5000},
        flood_states={"Z02": 0.0},
        bottlenecks={"Z02": 1.8},
        panic_states={"Z02": 0.9},
        infra_states={},
        time_step_seconds=3600.0,
    )
    assert res["total_injuries"] > 0
    assert res["total_fatalities"] > 0
