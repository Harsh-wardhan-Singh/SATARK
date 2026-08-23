class WaterModel:
    def __init__(self, zone_data, adjacency_list):
        """
        Initializes the water simulation.
        zone_data: dict containing elevation and drainage capacity per zone.
        adjacency_list: dict mapping zone_ids to lists of neighboring zone_ids.
        """
        self.zones = zone_data
        self.adjacency = adjacency_list
        
        # Initial water states (meters above ground level)
        self.water_levels = {zone_id: 0.0 for zone_id in self.zones.keys()}

    def calculate_next_state(self, rainfall_mm_per_hour):
        """
        Advances the water model by one discrete time step (e.g., 1 hour).
        Uses elevation gradients to calculate flow vectors between adjacent nodes.
        """
        next_levels = self.water_levels.copy()
        
        # Convert rainfall to meters
        rain_m = rainfall_mm_per_hour / 1000.0
        
        for zone_id, current_water in self.water_levels.items():
            zone_info = self.zones[zone_id]
            elevation = zone_info['elevation']
            
            # 1. Add rain and subtract drainage (cannot drain below 0)
            net_water = current_water + rain_m - zone_info['drainage_rate']
            next_levels[zone_id] = max(0.0, net_water)
            
            # 2. Calculate flow to/from neighbors based on absolute water height
            # Absolute height = ground elevation + current water depth
            absolute_height = elevation + self.water_levels[zone_id]
            
            for neighbor_id in self.adjacency.get(zone_id, []):
                neighbor_info = self.zones[neighbor_id]
                neighbor_absolute_height = neighbor_info['elevation'] + self.water_levels[neighbor_id]
                
                # If this zone is higher than its neighbor, water flows outward
                gradient = absolute_height - neighbor_absolute_height
                
                if gradient > 0 and self.water_levels[zone_id] > 0:
                    # Flow rate scales with the gradient (steeper = faster)
                    flow_volume = min(self.water_levels[zone_id], gradient * 0.1) 
                    
                    # Apply shifts to the next state
                    next_levels[zone_id] -= flow_volume
                    next_levels[neighbor_id] += flow_volume
                    
        self.water_levels = next_levels
        return self.water_levels