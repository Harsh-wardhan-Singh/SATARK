class StateFeatureExtractor:
    def __init__(self, zone_ids, infra_ids):
        """
        Initializes the extractor with a fixed order of zones and infrastructure.
        The order must remain constant so the ML model always receives 
        the same feature at the same array index.
        """
        self.zone_ids = sorted(zone_ids)
        self.infra_ids = sorted(infra_ids)
        
        # Calculate expected vector size for validation
        # Per Zone: [water_level, bottleneck, panic_level, casualty_ratio]
        # Per Infra: [operational_capacity]
        self.vector_size = (len(self.zone_ids) * 4) + len(self.infra_ids)

    def extract_features(self, flood_states, bottlenecks, panic_states, casualties_data, infra_states, base_populations):
        """
        Flattens the entire multi-dimensional simulation state into a single 
        normalized 1D list (vector) for ML model consumption.
        """
        feature_vector = []

        # 1. Zone-Level Features (4 features per zone)
        for zone in self.zone_ids:
            # Feature A: Water Level (Normalized to assumed max depth of 5.0m)
            water_depth = flood_states.get(zone, 0.0)
            feature_vector.append(min(water_depth / 5.0, 1.0))
            
            # Feature B: Bottleneck Severity (Normalized to assumed max of 3.0 ratio)
            congestion = bottlenecks.get(zone, 0.0)
            feature_vector.append(min(congestion / 3.0, 1.0))
            
            # Feature C: Panic State (Already 0.0 to 1.0)
            panic = panic_states.get(zone, 0.0)
            feature_vector.append(panic)
            
            # Feature D: Casualty Ratio (Injuries + Fatalities / Base Population)
            zone_cas = casualties_data.get(zone, {"fatalities": 0, "injuries": 0})
            total_cas = zone_cas["fatalities"] + zone_cas["injuries"]
            base_pop = base_populations.get(zone, 1) # Avoid division by zero
            feature_vector.append(min(total_cas / base_pop, 1.0))

        # 2. Infrastructure-Level Features (1 feature per node)
        for infra in self.infra_ids:
            # Feature E: Operational Capacity (Already 0.0 to 1.0)
            state = infra_states.get(infra, {'capacity': 1.0})
            # Handle both raw float states and dictionary states depending on the engine's exact output
            capacity = state['capacity'] if isinstance(state, dict) else state
            feature_vector.append(capacity)

        # 3. Validation
        if len(feature_vector) != self.vector_size:
            raise ValueError(f"Feature vector shape mismatch. Expected {self.vector_size}, got {len(feature_vector)}")

        return feature_vector