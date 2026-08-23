import { Agent, AgentSnapshot, RawAgentDTO, RawAgentSnapshotDTO } from '../types/domain';
import { validateAgent, validateAgentSnapshot } from '../utils/agentValidation';

/**
 * Agent API Contract Boundary for SATARK Digital Twin.
 * 
 * Normalizes raw Django REST Framework JSON snapshots into authoritative Agent domain models.
 * 
 * NOTE: The backend agent API endpoints are currently under development.
 * This module establishes the validation and ingestion contract WITHOUT fabricating
 * fake endpoints or fake NPC datasets.
 */

/**
 * Normalizes a raw agent DTO received from the backend into a domain Agent object.
 * Returns null if the DTO fails validation.
 */
export function normalizeAgent(raw: RawAgentDTO): Agent | null {
  return validateAgent(raw);
}

/**
 * Normalizes a raw agent snapshot payload received from the backend.
 * Returns null if the payload fails validation.
 */
export function normalizeAgentSnapshot(raw: RawAgentSnapshotDTO): AgentSnapshot | null {
  return validateAgentSnapshot(raw);
}

/**
 * Fetches the latest authoritative agent snapshot from the backend.
 * 
 * CONTRACT STUB:
 * Real Django REST Framework endpoint (e.g. GET /api/v1/simulation/agents/) will be connected
 * in a subsequent phase once the backend agent simulation service is deployed.
 */
export const fetchAgentsSnapshot = async (_tick?: number): Promise<AgentSnapshot> => {
  throw new Error('Not implemented: fetchAgentsSnapshot. Backend DRF endpoint not yet available.');
};
