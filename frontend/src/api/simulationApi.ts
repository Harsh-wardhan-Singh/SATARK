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

export interface NowcastHorizonProjection {
  horizon_hours: number;
  water_depth_cm: Record<string, number>;
  delta_depth_cm: Record<string, number>;
  critical_zones: string[];
}

export interface NowcastResponse {
  current_tick: number;
  horizons: NowcastHorizonProjection[];
}

export const fetchNowcast = async (horizons?: number[]): Promise<NowcastResponse> => {
  const query = horizons ? `?horizons=${horizons.join(',')}` : '';
  const data = await apiClient.get(`/simulation/nowcast/${query}`);
  return data;
};

export interface DisasterScenarioPreset {
  id: string;
  name: string;
  description: string;
  duration_days: number;
  duration_seconds: number;
  severity: number;
  severity_label: string;
  rainfall_intensity: number;
  hyetograph_type: string;
  target_zone: string;
  target_ward: string;
}

export const fetchSimulationPresets = async (): Promise<DisasterScenarioPreset[]> => {
  const data = await apiClient.get('/simulation/presets/');
  return data?.presets || [];
};
