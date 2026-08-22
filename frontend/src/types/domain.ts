export type CalamityType = 'Flood' | 'Earthquake';

export interface Zone {
  id: string;
  name: string;
}

export interface SafeZone {
  id: string;
  zoneId: string;
  capacity: number;
}

export interface Agent {
  id: string;
  zoneId: string;
}

export interface Calamity {
  type: CalamityType;
  active: boolean;
}

export interface SimulationSnapshot {
  tick: number;
  // Will contain backend data later
}

export interface Simulation {
  activeCalamity: Calamity | null;
  status: 'idle' | 'running' | 'paused';
  currentTick: number;
}
