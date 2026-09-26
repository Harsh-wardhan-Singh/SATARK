import json
import tempfile
from pathlib import Path
import pytest
from algorithms.infrastructure.cascade import ExplainableNetwork

@pytest.fixture
def sample_infra_path():
    data = {
        "infrastructure": [
            {
                "id": "power_plant",
                "name": "Central Power Plant",
                "type": "power",
                "zone_id": "Z01",
                "vulnerability_threshold": 0.4,
                "backup_power": 0.0,
                "depends_on": []
            },
            {
                "id": "water_treatment",
                "name": "Water Treatment Facility",
                "type": "water",
                "zone_id": "Z02",
                "vulnerability_threshold": 0.7,
                "backup_power": 0.2,
                "depends_on": [
                    {"parent_id": "power_plant", "weight": 1.0}
                ]
            }
        ]
    }
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(data, f)
        temp_path = f.name
    yield temp_path
    Path(temp_path).unlink(missing_ok=True)

def test_infrastructure_initial_state(sample_infra_path):
    network = ExplainableNetwork(sample_infra_path)
    assert len(network.nodes) == 2
    assert network.nodes["power_plant"]["capacity"] == 1.0
    assert network.nodes["water_treatment"]["capacity"] == 1.0

def test_infrastructure_direct_damage(sample_infra_path):
    network = ExplainableNetwork(sample_infra_path)
    
    # Impact 0.6 on Z01 (threshold is 0.4 -> damage = (0.6 - 0.4)*2 = 0.4 -> local_health = 0.6)
    states = network.simulate_timestep({"Z01": 0.6, "Z02": 0.0})
    
    power_node = states["power_plant"]
    assert power_node["capacity"] == pytest.approx(0.6)
    assert "Direct Flood Damage" in power_node["status_reason"]

def test_infrastructure_cascade_failure(sample_infra_path):
    network = ExplainableNetwork(sample_infra_path)
    
    # Timestep 1: Severe flood destroys power plant (impact 1.0 -> capacity = 0.0)
    network.simulate_timestep({"Z01": 1.0, "Z02": 0.0})
    assert network.nodes["power_plant"]["capacity"] == pytest.approx(0.0)
    
    # Timestep 2: Failure cascades to water treatment plant dependent on power
    states = network.simulate_timestep({"Z01": 1.0, "Z02": 0.0})
    water_node = states["water_treatment"]
    assert water_node["capacity"] == pytest.approx(0.2)
    assert "Cascading failure" in water_node["status_reason"]
