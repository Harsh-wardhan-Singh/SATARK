import json
import math
import numpy as np

# Load zones
with open('backend/data/glb_zone_mapping.json', 'r') as f:
    zone_data = json.load(f)['zones']

zones = {z['id']: z for z in zone_data}
zone_ids = list(zones.keys())
N = len(zone_ids)
zone_idx = {zid: i for i, zid in enumerate(zone_ids)}

# Real terrain elevation scaled from normalized [0, 1] to meters [5.0m, 35.0m]
elevations = np.array([5.0 + zones[zid]['center_normalized']['y'] * 30.0 for zid in zone_ids])
positions = np.array([[zones[zid]['center_world']['x'], zones[zid]['center_world']['z']] for zid in zone_ids])

# Adjacency and distances
adj = np.zeros((N, N), dtype=bool)
dist = np.full((N, N), np.inf)

for zid, z in zones.items():
    i = zone_idx[zid]
    for nid in z.get('neighbors', []):
        if nid in zone_idx:
            j = zone_idx[nid]
            adj[i, j] = True
            d = math.sqrt(np.sum((positions[i] - positions[j])**2)) * 0.25
            dist[i, j] = max(50.0, d)

# Water depth in meters
W = np.zeros(N)

# Add initial water to high zones
W[zone_idx['Z01']] = 1.0  # 1 meter of water in Z01
initial_mass = np.sum(W)

# Flow conductivity
k_flow = 0.5

# Step 1: Hydraulic heads
H = elevations + W

# Step 2: Gradients
dH = H[:, None] - H[None, :]  # dH[i, j] = H[i] - H[j]
gradients = np.where(adj, np.maximum(0.0, dH) / dist, 0.0)

# Outflow demand per zone: q[i, j]
q_demand = gradients * k_flow

# Total outward demand per zone
Q_out_demand = np.sum(q_demand, axis=1)

# Alpha clamping factor: water cannot exceed what is available
alpha = np.where(Q_out_demand > 0, np.minimum(1.0, W / (Q_out_demand + 1e-9)), 1.0)

# Actual conserved flux matrix
F = q_demand * alpha[:, None]

# Net inter-zone transfer: inflow - outflow
net_transfer = np.sum(F, axis=0) - np.sum(F, axis=1)

# Mass conservation check on inter-zone flow: sum of net_transfer must be 0.0
mass_flux_error = np.sum(net_transfer)
print(f"Net inter-zone flux sum: {mass_flux_error:.12f}")
assert abs(mass_flux_error) < 1e-12

# Update water depths
W_new = W + net_transfer
final_mass = np.sum(W_new)
mass_error = abs(final_mass - initial_mass) / initial_mass * 100.0

print(f"Initial total water: {initial_mass:.6f} m")
print(f"Final total water:   {final_mass:.6f} m")
print(f"Mass balance error:  {mass_error:.8f}%")
print(f"Z01 water: {W[zone_idx['Z01']]:.4f}m -> {W_new[zone_idx['Z01']]:.4f}m")
for n in zones['Z01']['neighbors']:
    print(f"  Neighbor {n} water: {W[zone_idx[n]]:.4f}m -> {W_new[zone_idx[n]]:.4f}m")
