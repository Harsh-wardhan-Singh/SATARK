import { Zone, SafeZone, Agent } from '../types/domain';
import { WorldBounds } from '../city/zones/voronoi';

/**
 * TEMPORARY DEVELOPMENT FIXTURE
 * Shared import helper so the JSON is loaded only once.
 */
async function loadZoneMapping(): Promise<Record<string, unknown>> {
  const response = await import('../../../backend/data/glb_zone_mapping.json');
  return (response.default || response) as Record<string, unknown>;
}

export const fetchZones = async (): Promise<Zone[]> => {
  // TEMPORARY DEVELOPMENT FIXTURE
  // Directly importing the backend data JSON because the real backend API endpoint does not exist yet.
  // This must be replaced with a real fetch (e.g. GET /api/zones) once the backend is ready.
  // IMPORTANT: Do not use this as production architecture.
  try {
    const data = await loadZoneMapping();
    
    if (!data.zones || !Array.isArray(data.zones)) {
      throw new Error("Invalid zone data format.");
    }
    
    if ((data.zones as unknown[]).length !== 21) {
      console.warn(`Expected 21 zones, got ${(data.zones as unknown[]).length}`);
    }

    return data.zones as Zone[];
  } catch (err) {
    console.error("Failed to load backend zone data:", err);
    throw err;
  }
};

/**
 * Extract the authoritative world bounds from glb_zone_mapping.json.
 * Used by the Voronoi visualization — NOT a new backend contract.
 */
export const fetchWorldBounds = async (): Promise<WorldBounds> => {
  try {
    const data = await loadZoneMapping();

    const wcs = data.world_coordinate_system as
      | { world_bounds?: { x_min?: number; x_max?: number; z_min?: number; z_max?: number } }
      | undefined;

    if (!wcs?.world_bounds) {
      throw new Error('Missing world_coordinate_system.world_bounds in zone mapping JSON');
    }

    const b = wcs.world_bounds;
    if (
      typeof b.x_min !== 'number' ||
      typeof b.x_max !== 'number' ||
      typeof b.z_min !== 'number' ||
      typeof b.z_max !== 'number'
    ) {
      throw new Error('Invalid world_bounds values in zone mapping JSON');
    }

    return {
      xMin: b.x_min,
      xMax: b.x_max,
      zMin: b.z_min,
      zMax: b.z_max,
    };
  } catch (err) {
    console.error('Failed to load world bounds:', err);
    throw err;
  }
};

export const fetchSafeZones = async (): Promise<SafeZone[]> => {
  // Safe zones remain backend-authoritative.
  // Since we don't have authoritative safe zone data yet, return empty.
  return Promise.resolve([]);
};

export const fetchAgents = async (): Promise<Agent[]> => {
  throw new Error('Not implemented: fetchAgents');
};
