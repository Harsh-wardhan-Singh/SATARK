export type CalamityType = 'Flood' | 'Earthquake';

export interface ZoneSpatial {
  type: 'point' | 'polygon' | 'unknown';
  coordinates: any; // Can be [x, y, z] for point, or GeoJSON for polygon, etc.
}

export interface Zone {
  id: string;
  name: string;
  spatial: ZoneSpatial;
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
