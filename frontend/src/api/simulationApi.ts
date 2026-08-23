import { CalamityType, WorldSnapshot, RawWorldSnapshotDTO } from '../types/domain';
import { validateWorldSnapshot } from '../utils/snapshotValidation';

/**
 * Normalizes a raw world snapshot payload received from the backend.
 * Returns null if the payload fails validation.
 */
export function normalizeWorldSnapshot(raw: RawWorldSnapshotDTO): WorldSnapshot | null {
  return validateWorldSnapshot(raw);
}

export const startSimulation = async (_calamityType: CalamityType): Promise<void> => {
  throw new Error('Not implemented: startSimulation. Backend DRF endpoint not yet available.');
};

/**
 * Fetches the authoritative world snapshot for a given tick from the backend.
 * 
 * CONTRACT STUB:
 * Real Django REST Framework endpoint will be connected in a subsequent phase.
 */
export const fetchWorldSnapshot = async (_tick: number): Promise<WorldSnapshot> => {
  throw new Error('Not implemented: fetchWorldSnapshot. Backend DRF endpoint not yet available.');
};
