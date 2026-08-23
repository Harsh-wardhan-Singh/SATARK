import math

class CrowdDynamicsEngine:
    def __init__(self, population_data, shelter_data):
        """
        Initializes the dynamic tracking of the population.
        """
        # Track current number of people standing in each zone (starts with residents)
        self.zone_populations = {
            z['zone_id']: z['resident_population_estimate'] 
            for z in population_data['zones']
        }
        
        # Track shelter occupancy
        self.shelters = {
            s['id']: {
                'zone_id': s['zone_id'], 
                'capacity': s['capacity'], 
                'current_occupancy': 0
            } 
            for s in shelter_data['shelters']
        }
        
        # Calculate maximum transient capacity per zone (using the footprint proxy as a base)
        # Assuming roughly 10% of a zone's footprint can be used for transit/roads
        self.transit_capacities = {
            z['zone_id']: z['building_footprint_proxy'] * 0.1 
            for z in population_data['zones']
        }

    def simulate_movement_step(self, evacuation_routes, panic_states):
        """
        Advances the crowd movement by one simulation tick (e.g., 1 hour).
        Returns a dictionary of bottleneck severities to feed the casualty engine.
        """
        # Track intended movements: {target_zone: [number_of_people_arriving]}
        movement_intentions = {zone: 0 for zone in self.zone_populations.keys()}
        bottlenecks = {}
        
        # 1. Calculate how many people attempt to leave their current zone
        for zone_id, current_pop in self.zone_populations.items():
            if current_pop <= 0:
                continue
                
            route_info = evacuation_routes.get(zone_id)
            
            # If no safe route, they are trapped (movement = 0)
            if not route_info or not route_info['safe'] or len(route_info['path']) <= 1:
                continue
                
            # The next step on their Dijkstra path
            next_zone = route_info['path'][1]
            
            # Base movement: 40% of people try to move per hour. 
            # Panic makes them rush (up to 80% try to move).
            panic = panic_states.get(zone_id, 0.0)
            movement_rate = 0.4 + (0.4 * panic) 
            
            people_moving = int(current_pop * movement_rate)
            movement_intentions[next_zone] += people_moving
            
            # Temporarily remove them from their origin zone (they are "in transit")
            self.zone_populations[zone_id] -= people_moving
            
        # 2. Resolve movements and bottlenecks at the destinations
        for target_zone, incoming_people in movement_intentions.items():
            if incoming_people == 0:
                bottlenecks[target_zone] = 0.0
                continue
                
            capacity = self.transit_capacities.get(target_zone, 5000)
            
            if incoming_people <= capacity:
                # Everyone fits easily
                self.zone_populations[target_zone] += incoming_people
                bottlenecks[target_zone] = 0.0
            else:
                # BOTTLENECK: Too many people. The surplus gets stuck in congestion.
                # In a more granular sim, they'd bounce back. Here, we just log the severe crowding.
                self.zone_populations[target_zone] += incoming_people
                
                # Bottleneck score: Ratio of demand to capacity (e.g., 1.5 = 50% over capacity)
                congestion_ratio = incoming_people / capacity
                bottlenecks[target_zone] = round(min(congestion_ratio, 3.0), 2) # Cap at 3.0
                
        # 3. Process people arriving at shelters
        self._intake_at_shelters()
        
        return {
            "zone_populations": self.zone_populations,
            "shelter_status": self.shelters,
            "bottlenecks": bottlenecks
        }
        
    def _intake_at_shelters(self):
        """
        Moves people from the street into the shelter if they are in a shelter zone.
        """
        for s_id, shelter in self.shelters.items():
            zone_id = shelter['zone_id']
            people_outside = self.zone_populations[zone_id]
            available_space = shelter['capacity'] - shelter['current_occupancy']
            
            if people_outside > 0 and available_space > 0:
                people_taken_in = min(people_outside, available_space)
                self.shelters[s_id]['current_occupancy'] += people_taken_in
                self.zone_populations[zone_id] -= people_taken_in