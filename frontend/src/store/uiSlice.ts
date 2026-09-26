import { StateCreator } from 'zustand';

export type WorkflowState = 'idle' | 'zone-selected' | 'disaster-active' | 'disaster-finished';
export type ViewportMode = '3d' | '2d';

export interface UiSlice {
  workflowState: WorkflowState;
  selectedZoneId: string | null;
  activePanel: string | null;
  viewportMode: ViewportMode;
  forecastHorizonHours: number;
  // Actions
  setWorkflowState: (state: WorkflowState) => void;
  setSelectedZoneId: (id: string | null) => void;
  setActivePanel: (panel: string | null) => void;
  setViewportMode: (mode: ViewportMode) => void;
  setForecastHorizonHours: (hours: number) => void;
}

export const createUiSlice: StateCreator<UiSlice> = (set) => ({
  workflowState: 'idle',
  selectedZoneId: null,
  activePanel: null,
  viewportMode: '3d',
  forecastHorizonHours: 0,
  setWorkflowState: (workflowState) => set({ workflowState }),
  setSelectedZoneId: (selectedZoneId) => set((state) => {
    // Automatically transition to 'zone-selected' if a zone is selected while in 'idle'
    if (selectedZoneId !== null && state.workflowState === 'idle') {
      return { selectedZoneId, workflowState: 'zone-selected' };
    }
    // If deselecting while in 'zone-selected', return to 'idle'
    if (selectedZoneId === null && state.workflowState === 'zone-selected') {
      return { selectedZoneId, workflowState: 'idle' };
    }
    return { selectedZoneId };
  }),
  setActivePanel: (activePanel) => set({ activePanel }),
  setViewportMode: (viewportMode) => set({ viewportMode }),
  setForecastHorizonHours: (forecastHorizonHours) => set({ forecastHorizonHours }),
});
