import json
import os

class ExplainableNetwork:
    def __init__(self, json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        self.nodes = {item['id']: item for item in data['infrastructure']}
        # Initialize running state
        for node in self.nodes.values():
            node['capacity'] = 1.0
            node['status_reason'] = "Operational"

    def simulate_timestep(self, flood_impacts):
        """
        flood_impacts: dict mapping zone_id -> ML impact_score (0.0 to 1.0)
        """
        new_states = {}
        
        for node_id, node in self.nodes.items():
            impact = flood_impacts.get(node['zone_id'], 0.0)
            
            # 1. Check Local Physical Damage
            # If impact exceeds the building's threshold, it starts failing locally
            local_health = 1.0
            if impact > node['vulnerability_threshold']:
                # The higher the impact above the threshold, the worse the damage
                damage = (impact - node['vulnerability_threshold']) * 2.0 
                local_health = max(0.0, 1.0 - damage)
            
            # 2. Check Dependency Failures (Cascading)
            dep_health = 1.0
            critical_failure_source = None
            
            if node['depends_on']:
                dep_score = 0.0
                for dep in node['depends_on']:
                    parent_cap = self.nodes[dep['parent_id']]['capacity']
                    dep_score += parent_cap * dep['weight']
                    
                    if parent_cap < 0.5:
                        critical_failure_source = self.nodes[dep['parent_id']]['name']
                
                # Apply backup generators if grid fails
                dep_health = node['backup_power'] + ((1.0 - node['backup_power']) * dep_score)

            # 3. Final Calculation & Explainability
            final_capacity = local_health * dep_health
            
            # Determine WHY it's failing for the frontend UI
            if final_capacity > 0.9:
                reason = "Fully Operational"
            elif local_health < dep_health:
                reason = f"Direct Flood Damage (Impact: {impact:.2f})"
            elif critical_failure_source:
                reason = f"Cascading failure: Lost connection to {critical_failure_source}"
            else:
                reason = "Degraded performance"
                
            new_states[node_id] = {
                'capacity': final_capacity,
                'status_reason': reason
            }
            
        # Apply updates
        for node_id, state in new_states.items():
            self.nodes[node_id]['capacity'] = state['capacity']
            self.nodes[node_id]['status_reason'] = state['status_reason']

    def export_for_ui(self):
        """Generates the exact JSON string Blender/Frontend needs to display."""
        ui_data = []
        for node in self.nodes.values():
            ui_data.append({
                "name": node['name'],
                "type": node['type'],
                "capacity": round(node['capacity'] * 100, 1),
                "reason": node['status_reason']
            })
        return json.dumps(ui_data, indent=2)

if __name__ == "__main__":
    # Test the explainable cascade with the EXPANDED infrastructure
    network = ExplainableNetwork("../data/infrastructure.json")
    
    # Scenario: The lowland (Zone 2) floods heavily, taking out the poles. 
    # Zone 3 (Water) and Zone 4 (Hospital) stay mostly dry.
    mock_flood = {
        "zone_1": 0.1,  # Substation is fine
        "zone_2": 0.8,  # Poles and Bridge are underwater (Thresholds 0.25 and 0.3)
        "zone_3": 0.0,  # Water station physically dry
        "zone_4": 0.0   # Hospital is completely dry
    }
    
    print("--- HOUR 1: FLOOD HITS LOWLANDS ---")
    network.simulate_timestep(mock_flood)
    print(network.export_for_ui())