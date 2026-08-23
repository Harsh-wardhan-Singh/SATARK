import { Zone } from '../../types/domain';

/**
 * Given a world coordinate (X and Z) and a list of authoritative zones,
 * returns the ID of the nearest zone.
 * 
 * Uses deterministic tie-breaking based on zone ID if distances are exactly equal.
 */
export function getZoneForWorldPosition(
  position: { x: number; z: number },
  zones: Zone[]
): string | null {
  if (!zones || zones.length === 0) {
    return null;
  }

  let nearestZoneId: string | null = null;
  let minDistanceSq = Infinity;

  for (const zone of zones) {
    const dx = position.x - zone.center_world.x;
    const dz = position.z - zone.center_world.z;
    const distSq = dx * dx + dz * dz;

    if (distSq < minDistanceSq) {
      minDistanceSq = distSq;
      nearestZoneId = zone.id;
    } else if (distSq === minDistanceSq && nearestZoneId) {
      // Deterministic tie-breaker
      if (zone.id < nearestZoneId) {
        nearestZoneId = zone.id;
      }
    }
  }

  return nearestZoneId;
}
