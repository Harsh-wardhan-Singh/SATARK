import { CalamityType, WorldSnapshot, RawWorldSnapshotDTO } from '../types/domain';
import { validateWorldSnapshot } from '../utils/snapshotValidation';
import { apiClient } from './client';

/**
 * Normalizes a raw world snapshot payload received from the backend.
 * Returns null if the payload fails validation.
 */
export function normalizeWorldSnapshot(raw: any): WorldSnapshot | null {
  if (!raw) return null;
  const payload = (raw && typeof raw === 'object' && ('state' in raw ? raw.state : 'data' in raw ? raw.data : raw)) as RawWorldSnapshotDTO;
  return validateWorldSnapshot(payload);
}

export interface SimulationInitPayload {
  duration: number;
  tick_rate: number;
  calamity_type: CalamityType;
  parameters: Record<string, any>;
}

export const teardownSimulation = async (): Promise<void> => {
  await apiClient.post('/simulation/teardown/');
};

export const fetchWorldSnapshot = async (_tick?: number): Promise<WorldSnapshot> => {
  const data = await apiClient.get('/simulation/state/');
  const snapshot = normalizeWorldSnapshot(data);
  if (!snapshot) {
    throw new Error('Received invalid world snapshot from backend');
  }
  return snapshot;
};

export const initializeSimulation = async (payload: SimulationInitPayload): Promise<WorldSnapshot> => {
  const data = await apiClient.post('/simulation/initialize/', payload);
  const snapshot = normalizeWorldSnapshot(data);
  if (!snapshot) {
    throw new Error('Received invalid world snapshot from backend');
  }
  return snapshot;
};

export const stepSimulation = async (): Promise<WorldSnapshot> => {
  const data = await apiClient.post('/simulation/step/');
  
  const snapshot = normalizeWorldSnapshot(data);
  
  if (!snapshot) {
    throw new Error('Received invalid world snapshot from backend');
  }
  return snapshot;
};

export const pauseSimulation = async (): Promise<WorldSnapshot> => {
  const data = await apiClient.post('/simulation/pause/');
  const snapshot = normalizeWorldSnapshot(data);
  if (!snapshot) {
    throw new Error('Received invalid world snapshot from backend');
  }
  return snapshot;
};

export const resumeSimulation = async (): Promise<WorldSnapshot> => {
  const data = await apiClient.post('/simulation/resume/');
  const snapshot = normalizeWorldSnapshot(data);
  if (!snapshot) {
    throw new Error('Received invalid world snapshot from backend');
  }
  return snapshot;
};

export const resetSimulation = async (): Promise<WorldSnapshot> => {
  const data = await apiClient.post('/simulation/reset/');
  const snapshot = normalizeWorldSnapshot(data);
  if (!snapshot) {
    throw new Error('Received invalid world snapshot from backend');
  }
  return snapshot;
};

export const applyIntervention = async (intervention_id: string): Promise<WorldSnapshot> => {
  const data = await apiClient.post('/simulation/intervention/', { intervention_id });
  const snapshot = normalizeWorldSnapshot(data);
  if (!snapshot) {
    throw new Error('Received invalid world snapshot from backend');
  }
  return snapshot;
};
