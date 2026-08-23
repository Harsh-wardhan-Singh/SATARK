import { create } from 'zustand';
import { createWorldSlice, WorldSlice } from './worldSlice';
import { createAgentSlice, AgentSlice } from './agentSlice';
import { createSimulationSlice, SimulationSlice } from './simulationSlice';
import { createUiSlice, UiSlice } from './uiSlice';

export type StoreState = WorldSlice & AgentSlice & SimulationSlice & UiSlice;

export const useStore = create<StoreState>()((...a) => ({
  ...createWorldSlice(...a),
  ...createAgentSlice(...a),
  ...createSimulationSlice(...a),
  ...createUiSlice(...a),
}));

export * from './worldSlice';
export * from './agentSlice';
export * from './simulationSlice';
export * from './uiSlice';
