import json

class FloodPropagator:
    def __init__(self, zone_mapping_path):
        with open(zone_mapping_path, 'r') as f:
            self.zone_data = json.load(f)['zones']
        
        # Initialize simulation state
        self.state = {}
        for z in self.zone_data:
            self.state[z['id']] = {
                'water_level': 0.0,
                'elevation': z['center_normalized']['y'],
                'neighbors': z['neighbors'],
                'drainage_capacity': 0.05 # Water removed per hour
            }
            
    def simulate_hour(self, rainfall_intensity):
        new_state = {}
        flow_k = 0.2 # Flow rate coefficient
        
        for zone_id, data in self.state.items():
            current_water = data['water_level']
            
            # 1. Add rainfall and remove drainage
            current_water += rainfall_intensity
            current_water -= data['drainage_capacity']
            
            # 2. Calculate flow from/to neighbors
            inflow = 0.0
            outflow = 0.0
            
            for neighbor_id in data['neighbors']:
                neighbor = self.state[neighbor_id]
                
                # Total height = terrain elevation + current water level
                my_height = data['elevation'] + current_water
                neighbor_height = neighbor['elevation'] + neighbor['water_level']
                
                height_diff = my_height - neighbor_height
                
                if height_diff > 0:
                    # Water flows out to lower neighbor
                    outflow += height_diff * flow_k
                else:
                    # Water flows in from higher neighbor
                    inflow += abs(height_diff) * flow_k
            
            # 3. Apply changes
            final_water = max(0.0, current_water + inflow - outflow)
            
            new_state[zone_id] = {
                'water_level': final_water,
                'elevation': data['elevation'],
                'neighbors': data['neighbors'],
                'drainage_capacity': data['drainage_capacity']
            }
            
        self.state = new_state
        return {z: self.state[z]['water_level'] for z in self.state}