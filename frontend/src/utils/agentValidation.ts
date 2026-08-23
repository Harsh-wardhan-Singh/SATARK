import { Agent, AgentState, AgentSnapshot, RawAgentDTO, RawAgentSnapshotDTO, Zone } from '../types/domain';
import { getZoneForWorldPosition } from '../city/utils/spatial';

const VALID_AGENT_STATES: Set<string> = new Set(['NORMAL', 'PANIC', 'SAFE']);

/**
 * Validates a single raw agent object and transforms it into an authoritative Agent domain object.
 * Returns null if the raw data is invalid or malformed.
 */
export function validateAgent(raw: unknown): Agent | null {
  if (!raw || typeof raw !== 'object') {
    console.warn('[AgentValidation] Invalid agent payload: expected object', raw);
    return null;
  }

  const dto = raw as RawAgentDTO;

  // 1. Validate ID
  if (!dto.id || typeof dto.id !== 'string' || dto.id.trim() === '') {
    console.warn('[AgentValidation] Invalid agent ID:', dto.id);
    return null;
  }

  // 2. Validate Position
  if (!dto.position || typeof dto.position !== 'object') {
    console.warn(`[AgentValidation] Agent ${dto.id} missing position object`);
    return null;
  }

  const x = Number(dto.position.x);
  const y = dto.position.y !== undefined ? Number(dto.position.y) : 0;
  const z = dto.position.z !== undefined ? Number(dto.position.z) : 0;

  if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) {
    console.warn(`[AgentValidation] Agent ${dto.id} has non-finite position coordinates:`, dto.position);
    return null;
  }

  // 3. Validate Zone ID (accepts zone_id or zoneId)
  const rawZoneId = dto.zone_id || dto.zoneId;
  if (!rawZoneId || typeof rawZoneId !== 'string' || rawZoneId.trim() === '') {
    console.warn(`[AgentValidation] Agent ${dto.id} missing zoneId`);
    return null;
  }

  // 4. Validate State
  let state: AgentState = 'NORMAL';
  if (dto.state) {
    const upperState = dto.state.toUpperCase();
    if (VALID_AGENT_STATES.has(upperState)) {
      state = upperState as AgentState;
    } else {
      console.warn(`[AgentValidation] Agent ${dto.id} has unknown state '${dto.state}', defaulting to 'NORMAL'`);
    }
  }

  // 5. Forward-compatible optional fields
  const targetFacilityId = dto.target_facility_id && typeof dto.target_facility_id === 'string'
    ? dto.target_facility_id
    : undefined;

  const speed = typeof dto.speed === 'number' && Number.isFinite(dto.speed) && dto.speed > 0
    ? dto.speed
    : undefined;

  return {
    id: dto.id,
    position: { x, y, z },
    zoneId: rawZoneId,
    state,
    ...(targetFacilityId ? { targetFacilityId } : {}),
    ...(speed !== undefined ? { speed } : {}),
  };
}

/**
 * Validates a snapshot payload containing an array of agents and optional tick/timestamp metadata.
 */
export function validateAgentSnapshot(raw: unknown): AgentSnapshot | null {
  if (!raw || typeof raw !== 'object') {
    console.warn('[AgentValidation] Invalid snapshot payload: expected object', raw);
    return null;
  }

  const dto = raw as RawAgentSnapshotDTO;

  if (!Array.isArray(dto.agents)) {
    console.warn('[AgentValidation] Invalid snapshot payload: agents must be an array');
    return null;
  }

  const validatedAgents: Agent[] = [];
  for (const rawAgent of dto.agents) {
    const valid = validateAgent(rawAgent);
    if (valid) {
      validatedAgents.push(valid);
    }
  }

  const tick = typeof dto.tick === 'number' && Number.isFinite(dto.tick) ? dto.tick : undefined;
  const timestamp = typeof dto.timestamp === 'number' && Number.isFinite(dto.timestamp) ? dto.timestamp : Date.now();

  return {
    tick,
    timestamp,
    agents: validatedAgents,
  };
}

/**
 * Diagnostic utility: Compares backend-authoritative agent zoneId with frontend-calculated
 * nearest-center zone.
 * 
 * IMPORTANT: Diagnostic only. The backend's zoneId is authoritative and must NOT be mutated.
 */
export function checkAgentZoneConsistency(
  agent: Agent,
  zones: Zone[]
): { isConsistent: boolean; calculatedZoneId: string | null } {
  if (!zones || zones.length === 0) {
    return { isConsistent: true, calculatedZoneId: null };
  }

  const calculatedZoneId = getZoneForWorldPosition({ x: agent.position.x, z: agent.position.z }, zones);
  const isConsistent = calculatedZoneId === agent.zoneId;

  return {
    isConsistent,
    calculatedZoneId,
  };
}
