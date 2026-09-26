import json
import math
from pathlib import Path

# Load zone mapping to get positions and elevations
with open('backend/data/glb_zone_mapping.json', 'r') as f:
    zone_data = json.load(f)

zones = {z['id']: z for z in zone_data['zones']}

# Base terrain scale factor to convert normalized elevation [0, 1] to real-world meters [5m, 35m]
def get_node_elev(norm_y):
    return round(5.0 + norm_y * 30.0, 2)

nodes = {}
pipes = []

# 1. Create Inlets for each zone (Z01 to Z21)
for zid, z in zones.items():
    norm_y = z['center_normalized']['y']
    elev = get_node_elev(norm_y)
    inlet_id = f"inlet_{zid}"
    nodes[inlet_id] = {
        "id": inlet_id,
        "type": "INLET",
        "zone_id": zid,
        "world_pos": z["center_world"],
        "elevation_m": elev,
        "invert_elevation_m": round(elev - 2.5, 2),
        "inlet_capacity_m3_s": round(0.5 + norm_y * 0.5, 3), # 0.5 to 1.0 m3/s per zone inlet
    }

# 2. Intermediate Junctions
# Strategic junction collectors in mid and low valleys
junction_configs = [
    ("junction_J01", "Z03", 0.65, {"x": -176500.0, "z": 156500.0}),
    ("junction_J02", "Z07", 0.57, {"x": -175800.0, "z": 156000.0}),
    ("junction_J03", "Z09", 0.55, {"x": -176200.0, "z": 155200.0}),
    ("junction_J04", "Z12", 0.47, {"x": -175500.0, "z": 154500.0}),
    ("junction_J05", "Z15", 0.39, {"x": -176000.0, "z": 153500.0}),
    ("junction_J06", "Z18", 0.33, {"x": -174800.0, "z": 153000.0}),
    ("junction_J07", "Z19", 0.32, {"x": -175200.0, "z": 152000.0}),
]

for j_id, zid, norm_y, pos in junction_configs:
    elev = get_node_elev(norm_y)
    nodes[j_id] = {
        "id": j_id,
        "type": "JUNCTION",
        "zone_id": zid,
        "world_pos": pos,
        "elevation_m": elev,
        "invert_elevation_m": round(elev - 3.0, 2),
        "inlet_capacity_m3_s": 0.0,
    }

# 3. Pump Stations in low-lying zones
pump_configs = [
    ("pump_P01", "Z14", 0.41, 1.5, {"x": -175100.0, "z": 153800.0}),
    ("pump_P02", "Z18", 0.32, 2.0, {"x": -174600.0, "z": 152800.0}),
    ("pump_P03", "Z20", 0.25, 2.5, {"x": -174900.0, "z": 151200.0}),
]

for p_id, zid, norm_y, p_cap, pos in pump_configs:
    elev = get_node_elev(norm_y)
    nodes[p_id] = {
        "id": p_id,
        "type": "PUMP_STATION",
        "zone_id": zid,
        "world_pos": pos,
        "elevation_m": elev,
        "invert_elevation_m": round(elev - 3.5, 2),
        "pump_capacity_m3_s": p_cap,
        "inlet_capacity_m3_s": 0.0,
    }

# 4. Outfalls (Discharge points at river/bay boundary)
outfall_configs = [
    ("outfall_NORTH", "Z06", 0.60, {"x": -176300.0, "z": 158200.0}),
    ("outfall_RIVER_WEST", "Z21", 0.24, {"x": -176800.0, "z": 151500.0}),
    ("outfall_BAY_SOUTH", "Z20", 0.23, {"x": -174500.0, "z": 150800.0}),
]

for o_id, zid, norm_y, pos in outfall_configs:
    elev = get_node_elev(norm_y)
    nodes[o_id] = {
        "id": o_id,
        "type": "OUTFALL",
        "zone_id": zid,
        "world_pos": pos,
        "elevation_m": elev,
        "invert_elevation_m": round(elev - 4.0, 2),
        "inlet_capacity_m3_s": 0.0,
    }

# 5. Define Directed Pipes (Gravity + Pump lines)
# Pipe connectivity connects zone inlets to junctions, junctions to junctions/pumps, and pumps to outfalls
pipe_links = [
    # High elevation zone connections to Junction J01 & outfall North
    ("inlet_Z01", "junction_J01", 0.8),
    ("inlet_Z02", "junction_J01", 0.8),
    ("inlet_Z03", "junction_J01", 0.9),
    ("inlet_Z05", "junction_J01", 0.8),
    ("inlet_Z06", "outfall_NORTH", 1.0),

    # Mid elevation zone connections to J02 & J03
    ("inlet_Z04", "junction_J03", 0.8),
    ("inlet_Z07", "junction_J02", 0.9),
    ("inlet_Z08", "junction_J03", 0.8),
    ("inlet_Z09", "junction_J03", 0.9),
    ("inlet_Z10", "junction_J02", 0.8),

    # Trunk line from upper junctions to mid junctions
    ("junction_J01", "junction_J03", 1.2),
    ("junction_J02", "junction_J04", 1.2),
    ("junction_J03", "junction_J04", 1.2),

    # Mid to lower zone connections to J04 & J05 & Pump P01
    ("inlet_Z11", "pump_P01", 0.9),
    ("inlet_Z12", "junction_J04", 0.9),
    ("inlet_Z13", "junction_J05", 0.9),
    ("inlet_Z14", "pump_P01", 1.0),
    ("inlet_Z15", "junction_J05", 0.9),

    ("junction_J04", "junction_J05", 1.4),
    ("junction_J04", "pump_P01", 1.2),
    ("pump_P01", "junction_J06", 1.4),

    # Lower zones to J06, J07, Pump P02
    ("inlet_Z16", "junction_J06", 0.9),
    ("inlet_Z17", "junction_J07", 0.9),
    ("inlet_Z18", "pump_P02", 1.0),
    ("inlet_Z19", "junction_J07", 1.0),

    ("junction_J05", "junction_J07", 1.4),
    ("junction_J06", "pump_P02", 1.4),
    ("pump_P02", "junction_J07", 1.5),

    # Deep low zones to Pump P03 and Outfalls
    ("inlet_Z20", "pump_P03", 1.2),
    ("inlet_Z21", "outfall_RIVER_WEST", 1.2),

    ("junction_J07", "pump_P03", 1.6),
    ("junction_J07", "outfall_RIVER_WEST", 1.6),
    ("pump_P03", "outfall_BAY_SOUTH", 1.8),
]

for idx, (from_n, to_n, diameter) in enumerate(pipe_links, 1):
    n1 = nodes[from_n]
    n2 = nodes[to_n]
    
    # Distance in 2D space (scaled)
    dx = n1['world_pos']['x'] - n2['world_pos']['x']
    dz = n1['world_pos']['z'] - n2['world_pos']['z']
    length = round(max(80.0, math.sqrt(dx*dx + dz*dz) * 0.25), 1)
    
    # Bed slope
    dz_elev = n1['invert_elevation_m'] - n2['invert_elevation_m']
    slope = round(max(0.001, dz_elev / length), 5) if length > 0 else 0.001
    
    # Manning roughness for concrete pipe
    roughness = 0.013
    
    # Manning capacity calculation: Q = (1/n) * A * R_h^(2/3) * S^(1/2)
    # A = pi * D^2 / 4, R_h = D / 4
    area = (math.pi * (diameter ** 2)) / 4.0
    r_h = diameter / 4.0
    capacity = round((1.0 / roughness) * area * (r_h ** (2.0 / 3.0)) * math.sqrt(slope), 3)
    
    pipe_id = f"pipe_{from_n.split('_')[-1]}_{to_n.split('_')[-1]}_{idx:02d}"
    pipes.append({
        "id": pipe_id,
        "from_node": from_n,
        "to_node": to_n,
        "diameter_m": diameter,
        "length_m": length,
        "slope": slope,
        "roughness": roughness,
        "full_capacity_m3_s": capacity,
    })

drainage_data = {
    "version": "1.0.0",
    "description": "Synthetic stormwater drainage pipe network topology mapped to 21 SATARK simulation zones.",
    "manning_roughness_default": 0.013,
    "nodes": nodes,
    "pipes": pipes,
    "zone_inlet_mapping": {f"Z{i:02d}": f"inlet_Z{i:02d}" for i in range(1, 22)},
}

target_path = Path("backend/data/drainage_network.json")
with open(target_path, "w", encoding="utf-8") as f:
    json.dump(drainage_data, f, indent=2)

print(f"Generated drainage_network.json with {len(nodes)} nodes and {len(pipes)} pipes.")
