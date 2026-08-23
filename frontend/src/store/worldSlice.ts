import { StateCreator } from 'zustand';
import { Zone, SafeZone, Agent } from '../types/domain';

export interface WorldSlice {
  zones: Zone[];
  safeZones: SafeZone[];
  agents: Agent[];
  // Actions
  setZones: (zones: Zone[]) => void;
  setSafeZones: (safeZones: SafeZone[]) => void;
  setAgents: (agents: Agent[]) => void;
}

export const createWorldSlice: StateCreator<WorldSlice> = (set) => ({
  zones: [],
  safeZones: [],
  agents: [],
  setZones: (zones) => set({ zones }),
  setSafeZones: (safeZones) => set({ safeZones }),
  setAgents: (agents) => set({ agents }),
});
