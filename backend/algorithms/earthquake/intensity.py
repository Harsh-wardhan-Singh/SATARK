import math

class SeismicEngine:
    def __init__(self, zone_data):
        """
        Initializes the earthquake engine.
        zone_data: dict of zone parameters including coordinates and soil_factor.
        """
        self.zones = zone_data

    def calculate_pga(self, epicenter_lat, epicenter_lon, magnitude, depth_km):
        """
        Calculates the Peak Ground Acceleration (PGA) in units of 'g' (gravity)
        for every zone based on a simplified attenuation relationship.
        """
        intensity_map = {}
        
        for zone_id, data in self.zones.items():
            # 1. Calculate surface distance using Haversine formula (in km)
            distance_km = self._haversine(epicenter_lat, epicenter_lon, data['lat'], data['lon'])
            
            # 2. Calculate Hypocentral distance (3D distance including depth)
            # R = sqrt(surface_distance^2 + depth^2)
            hypocentral_distance = math.sqrt(distance_km**2 + depth_km**2)
            
            # 3. Apply a standard Attenuation Formula for PGA
            # This is a simplified Esteva-style equation where PGA decays with distance
            # and scales exponentially with magnitude.
            base_pga = (0.015 * (10 ** (0.432 * magnitude))) / ((hypocentral_distance + 0.1) ** 1.22)
            
            # 4. Apply Local Soil Amplification
            # Bedrock = ~0.8 (dampens), Average Soil = 1.0, Soft Soil/Mud = ~1.5 (amplifies)
            soil_factor = data.get('soil_factor', 1.0)
            final_pga = base_pga * soil_factor
            
            # Cap PGA at a realistic maximum (e.g., 2.5g for extreme quakes)
            intensity_map[zone_id] = round(min(final_pga, 2.5), 4)
            
        return intensity_map

    def _haversine(self, lat1, lon1, lat2, lon2):
        """
        Calculates the great-circle distance between two points on the Earth.
        """
        R = 6371.0 # Radius of Earth in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) * math.sin(dlon / 2))
             
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c