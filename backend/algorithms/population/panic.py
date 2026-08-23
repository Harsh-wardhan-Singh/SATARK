import json

class PanicEngine:
    def __init__(self, population_data):
        """
        Initializes the panic state using the Z01-Z21 population weights.
        """
        self.zones = {z['zone_id']: z for z in population_data['zones']}
        
        # State tracks panic level 0.0 to 1.0 per zone (starts completely calm)
        self.panic_state = {z['zone_id']: 0.0 for z in population_data['zones']}

    def update_panic(self, flood_impacts, infra_states):
        """
        Calculates the new panic level based on water levels and infrastructure failure.
        
        flood_impacts: dict mapping zone_id (e.g., 'Z01') -> ML impact_score
        infra_states: dict of infrastructure node data from ExplainableNetwork
        """
        new_panic = {}
        
        for zone_id, zone_info in self.zones.items():
            current_panic = self.panic_state[zone_id]
            
            # 1. Hazard Factor: How bad is the physical flood here right now?
            hazard_level = flood_impacts.get(zone_id, 0.0)
            
            # 2. Isolation/Blackout Factor: Have we lost power or comms?
            zone_infra = [n for n in infra_states.values() if n.get('zone_id') == zone_id]
            if zone_infra:
                # Average health of local infrastructure (0.0 = completely failed, 1.0 = fine)
                avg_infra_health = sum(n['capacity'] for n in zone_infra) / len(zone_infra)
                isolation_stress = 1.0 - avg_infra_health
            else:
                isolation_stress = 0.0 # No critical infra in this zone to fail
            
            # 3. Density Multiplier: Densely populated zones panic faster (Crowd Crush effect)
            # We scale the population weight to act as an escalator for panic
            density_multiplier = 1.0 + (zone_info['population_weight'] * 2.0)
            
            # Calculate the delta (change in panic for this hour)
            # Panic spikes rapidly with hazard and darkness, decays slowly when safe
            if hazard_level > 0.1 or isolation_stress > 0.2:
                # Increase panic
                panic_increase = ((hazard_level * 0.4) + (isolation_stress * 0.3)) * density_multiplier
                current_panic += panic_increase
            else:
                # Decay panic (calming down if safe)
                current_panic -= 0.1 
                
            # Clamp value strictly between 0.0 (calm) and 1.0 (mass hysteria)
            new_panic[zone_id] = max(0.0, min(1.0, current_panic))
            
        self.panic_state = new_panic
        return self.panic_state

if __name__ == "__main__":
    # Test the engine with dummy data
    mock_pop = {
        "zones": [
            {"zone_id": "Z01", "population_weight": 0.05},
            {"zone_id": "Z20", "population_weight": 0.14} # High density zone
        ]
    }
    mock_flood = {"Z01": 0.0, "Z20": 0.8}
    mock_infra = {
        "node1": {"zone_id": "Z20", "capacity": 0.0} # Total blackout in Z20
    }
    
    engine = PanicEngine(mock_pop)
    print("Hour 1 Panic Levels:", engine.update_panic(mock_flood, mock_infra))