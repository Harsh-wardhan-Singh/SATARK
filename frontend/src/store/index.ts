import { create } from 'zustand';
import { createWorldSlice, WorldSlice } from './worldSlice';
import { createSimulationSlice, SimulationSlice } from './simulationSlice';
import { createUiSlice, UiSlice } from './uiSlice';

export type StoreState = WorldSlice & SimulationSlice & UiSlice;

export const useStore = create<StoreState>()((...a) => ({
  ...createWorldSlice(...a),
  ...createSimulationSlice(...a),
  ...createUiSlice(...a),
}));
