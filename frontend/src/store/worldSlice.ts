import { StateCreator } from 'zustand';
import { Zone, SafeZone } from '../types/domain';

export interface WorldSlice {
  zones: Zone[];
  safeZones: SafeZone[];
  // Actions
  setZones: (zones: Zone[]) => void;
  setSafeZones: (safeZones: SafeZone[]) => void;
}

export const createWorldSlice: StateCreator<WorldSlice> = (set) => ({
  zones: [],
  safeZones: [],
  setZones: (zones) => set({ zones }),
  setSafeZones: (safeZones) => set({ safeZones }),
});
