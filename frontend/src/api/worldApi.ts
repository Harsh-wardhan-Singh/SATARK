import { Zone, SafeZone, Agent } from '../types/domain';

const USE_MOCK_DATA = false;

// DEVELOPMENT FIXTURES
// These mock data are purely for testing Phase 3 frontend rendering 
// until the real backend contract is established.
const MOCK_ZONES: Zone[] = [
  { id: 'zone-1', name: 'Downtown Sector', spatial: { type: 'point', coordinates: [700, 0, 700] } },
  { id: 'zone-2', name: 'Industrial Sector', spatial: { type: 'point', coordinates: [300, 0, 800] } },
  { id: 'zone-3', name: 'Residential Sector', spatial: { type: 'point', coordinates: [900, 0, 300] } },
];

const MOCK_SAFE_ZONES: SafeZone[] = [
  { id: 'sz-1', zoneId: 'zone-3', capacity: 5000 },
];

export const fetchZones = async (): Promise<Zone[]> => {
  if (USE_MOCK_DATA) return Promise.resolve(MOCK_ZONES);
  return Promise.resolve([]); // Backend world data unavailable
};

export const fetchSafeZones = async (): Promise<SafeZone[]> => {
  if (USE_MOCK_DATA) return Promise.resolve(MOCK_SAFE_ZONES);
  return Promise.resolve([]); // Backend world data unavailable
};

export const fetchAgents = async (): Promise<Agent[]> => {
  throw new Error('Not implemented: fetchAgents');
};
