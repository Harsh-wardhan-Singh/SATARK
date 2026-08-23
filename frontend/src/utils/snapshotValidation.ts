import { WorldSnapshot, RawWorldSnapshotDTO, SimulationStatus } from '../types/domain';
import { validateAgentSnapshot } from './agentValidation';

const VALID_STATUSES: Set<string> = new Set(['idle', 'running', 'paused']);

/**
 * Validates a raw world snapshot payload and normalizes it into an authoritative WorldSnapshot domain object.
 * Returns null if the raw data is invalid or malformed.
 */
export function validateWorldSnapshot(raw: unknown): WorldSnapshot | null {
  if (!raw || typeof raw !== 'object') {
    console.warn('[SnapshotValidation] Invalid world snapshot payload: expected object', raw);
    return null;
  }

  const dto = raw as RawWorldSnapshotDTO;

  // 1. Validate agents snapshot part
  // We pass the entire dto to validateAgentSnapshot because it expects { tick, timestamp, agents }
  const agentSnapshot = validateAgentSnapshot(dto);
  
  if (!agentSnapshot) {
    console.warn('[SnapshotValidation] Failed to validate agents within world snapshot');
    return null;
  }

  // 2. Extract Simulation Metadata
  const tick = typeof dto.tick === 'number' && Number.isFinite(dto.tick) ? dto.tick : 0;
  const timestamp = typeof dto.timestamp === 'number' && Number.isFinite(dto.timestamp) ? dto.timestamp : Date.now();
  
  let status: SimulationStatus | undefined = undefined;
  if (dto.status) {
    const lowerStatus = dto.status.toLowerCase();
    if (VALID_STATUSES.has(lowerStatus)) {
      status = lowerStatus as SimulationStatus;
    } else {
      console.warn(`[SnapshotValidation] Unknown simulation status '${dto.status}', ignoring`);
    }
  }

  // 3. Extract Zone States if any
  const zoneStates = dto.zone_states && typeof dto.zone_states === 'object' 
    ? (dto.zone_states as Record<string, unknown>)
    : undefined;

  return {
    simulation: {
      tick,
      timestamp,
      ...(status ? { status } : {})
    },
    agents: agentSnapshot,
    ...(zoneStates ? { zoneStates } : {})
  };
}
