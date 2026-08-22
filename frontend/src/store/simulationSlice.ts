import { StateCreator } from 'zustand';
import { Calamity } from '../types/domain';

export interface SimulationSlice {
  activeCalamity: Calamity | null;
  status: 'idle' | 'running' | 'paused';
  currentTick: number;
  // Actions
  setActiveCalamity: (calamity: Calamity | null) => void;
  setStatus: (status: 'idle' | 'running' | 'paused') => void;
  setCurrentTick: (tick: number) => void;
}

export const createSimulationSlice: StateCreator<SimulationSlice> = (set) => ({
  activeCalamity: null,
  status: 'idle',
  currentTick: 0,
  setActiveCalamity: (activeCalamity) => set({ activeCalamity }),
  setStatus: (status) => set({ status }),
  setCurrentTick: (currentTick) => set({ currentTick }),
});
