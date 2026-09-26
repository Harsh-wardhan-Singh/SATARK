import { Zone, SafeZone } from '../types/domain';
import { WorldBounds } from '../city/zones/voronoi';
import { apiClient } from './client';

export interface RouteWaypoint {
  zone_id: string;
  x: number;
  z: number;
  water_depth_m: number;
  water_depth_cm: number;
  panic_score: number;
  is_safe: boolean;
}

export interface RouteNavigationResponse {
  status: 'SUCCESS' | 'PARTIAL_HAZARD' | 'NO_PATH_FOUND' | 'INVALID_ZONE';
  origin_zone: string;
  destination_zone: string;
  path: string[];
  waypoints: RouteWaypoint[];
  total_distance_m: number;
  estimated_travel_time_min: number;
  safety_score: number;
  is_safe: boolean;
  depth_profile_cm: number[];
  max_water_depth_cm: number;
  impassable_zones_encountered: string[];
  warning_message?: string | null;
}

/**
 * Fetch the authoritative list of 21 simulation zones from GET /api/world/zones/.
 */
export const fetchZones = async (): Promise<Zone[]> => {
  try {
    const data = await apiClient.get('/world/zones/');
    if (data?.zones && Array.isArray(data.zones)) {
      if (data.zones.length !== 21) {
        console.warn(`Expected 21 zones from backend, got ${data.zones.length}`);
      }
      return data.zones as Zone[];
    }
    throw new Error('Invalid zone response structure from /api/world/zones/');
  } catch (err) {
    console.error('Failed to load zones via HTTP API:', err);
    throw err;
  }
};

/**
 * Fetch authoritative world bounds from GET /api/world/bounds/.
 */
export const fetchWorldBounds = async (): Promise<WorldBounds> => {
  try {
    const data = await apiClient.get('/world/bounds/');
    const b = data?.bounds;
    if (
      b &&
      typeof b.x_min === 'number' &&
      typeof b.x_max === 'number' &&
      typeof b.z_min === 'number' &&
      typeof b.z_max === 'number'
    ) {
      return {
        xMin: b.x_min,
        xMax: b.x_max,
        zMin: b.z_min,
        zMax: b.z_max,
      };
    }
    throw new Error('Invalid bounds structure from /api/world/bounds/');
  } catch (err) {
    console.error('Failed to load world bounds via HTTP API:', err);
    throw err;
  }
};

/**
 * Fetch municipal emergency shelters from GET /api/world/shelters/.
 */
export const fetchSafeZones = async (): Promise<SafeZone[]> => {
  try {
    const data = await apiClient.get('/world/shelters/');
    if (data?.shelters && Array.isArray(data.shelters)) {
      return data.shelters.map((s: any) => ({
        id: String(s.id || s.shelter_id),
        zoneId: String(s.zoneId || s.zone_id),
        capacity: Number(s.capacity) || 0,
      }));
    }
    return [];
  } catch (err) {
    console.warn('Failed to load shelters via HTTP API, returning empty:', err);
    return [];
  }
};

/**
 * Request a flood-safe transit/evacuation route avoiding waters > 30 cm from POST /api/navigation/route/.
 */
export const fetchFloodSafeRoute = async (
  origin: string | { x: number; z: number },
  destination: string | { x: number; z: number },
  allowFlooded: boolean = false
): Promise<RouteNavigationResponse> => {
  const payload: Record<string, any> = { allow_flooded: allowFlooded };
  if (typeof origin === 'string') {
    payload.origin_zone = origin;
  } else {
    payload.origin = origin;
  }
  if (typeof destination === 'string') {
    payload.destination_zone = destination;
  } else {
    payload.destination = destination;
  }
  return (await apiClient.post('/navigation/route/', payload)) as RouteNavigationResponse;
};
