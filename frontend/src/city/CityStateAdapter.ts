export interface CityStateAdapter {
  // Placeholder interface for the future renderer architecture
  // This will eventually sync Zustand state down to the Three.js CityRenderer
  syncWorldState: () => void;
  syncSimulationState: () => void;
}
