import { CalamityType, SimulationSnapshot } from '../types/domain';

export const startSimulation = async (_calamityType: CalamityType): Promise<void> => {
  throw new Error('Not implemented: startSimulation');
};

export const fetchSimulationSnapshot = async (_tick: number): Promise<SimulationSnapshot> => {
  throw new Error('Not implemented: fetchSimulationSnapshot');
};
