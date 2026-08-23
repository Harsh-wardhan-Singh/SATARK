import { StateCreator } from 'zustand';

export interface UiSlice {
  selectedZoneId: string | null;
  activePanel: string | null;
  // Actions
  setSelectedZoneId: (id: string | null) => void;
  setActivePanel: (panel: string | null) => void;
}

export const createUiSlice: StateCreator<UiSlice> = (set) => ({
  selectedZoneId: null,
  activePanel: null,
  setSelectedZoneId: (selectedZoneId) => set({ selectedZoneId }),
  setActivePanel: (activePanel) => set({ activePanel }),
});
