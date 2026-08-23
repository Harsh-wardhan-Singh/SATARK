import json
import pandas as pd
import numpy as np
import random
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

def load_base_data():
    with open(os.path.join(PROJECT_ROOT, 'data', 'population.json'), 'r') as f:
        pop_data = json.load(f)['zones']
    with open(os.path.join(PROJECT_ROOT, 'data', 'glb_zone_mapping.json'), 'r') as f:
        zone_data = json.load(f)['zones']
    
    zones = {}
    for p in pop_data:
        zones[p['zone_id']] = {'population': p['resident_population_estimate']}
    for z in zone_data:
        zones[z['id']]['elevation'] = z['center_normalized']['y']
    return zones

def generate_dataset(zones, samples=10000):
    data = []
    for _ in range(samples):
        zone_id = random.choice(list(zones.keys()))
        zone = zones[zone_id]
        
        # Explicit inputs matching train.py
        elevation = zone['elevation'] # 0.0 to 1.0
        flood_exposure = 1.0 - elevation
        severity = random.choice([1, 2, 3]) # 1, 2, 3
        day = random.randint(1, 7) # 1 to 7
        intervention = random.uniform(0.0, 1.0)
        drainage_weakness = random.uniform(0.0, 1.0)
        infra_vuln = random.uniform(0.0, 1.0)
        
        # Fully aligned impact equation (0.0 to 1.0 range)
        sev_norm = severity / 3.0
        day_norm = day / 7.0
        
        raw_impact = (
            (0.30 * flood_exposure) +
            (0.25 * sev_norm) +
            (0.15 * drainage_weakness) +
            (0.15 * infra_vuln) +
            (0.10 * day_norm) -
            (0.25 * intervention) # Strong intervention reduces impact directly
        )
        
        # Add slight noise and clamp strictly to [0.0, 1.0]
        noise = np.random.normal(0, 0.02)
        final_impact = float(np.clip(raw_impact + noise, 0.0, 1.0))
        
        data.append({
            'zone_id': zone_id,
            'elevation': elevation,
            'flood_exposure': flood_exposure,
            'severity': severity,
            'day': day,
            'intervention': intervention,
            'drainage_weakness': drainage_weakness,
            'infra_vuln': infra_vuln,
            'impact_score': round(final_impact, 4)
        })
        
    df = pd.DataFrame(data)
    out_dir = os.path.join(PROJECT_ROOT, 'data', 'raw')
    os.makedirs(out_dir, exist_ok=True)
    df.to_csv(os.path.join(out_dir, 'flood_model_training.csv'), index=False)
    print(f"Generated {samples} rows of synchronized dataset.")

if __name__ == "__main__":
    zones = load_base_data()
    generate_dataset(zones)