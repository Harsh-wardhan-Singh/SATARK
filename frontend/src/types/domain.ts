export type CalamityType = 'Flood' | 'Earthquake';

export interface WorldCoordinate {
  x: number;
  z: number;
}

export interface NormalizedCoordinate {
  x: number;
  y: number;
}

export interface Zone {
  id: string;
  name?: string;
  center_world: WorldCoordinate;
  center_normalized?: NormalizedCoordinate;
  neighbors: string[];
}

export interface SafeZone {
  id: string;
  zoneId: string;
  capacity: number;
}

export * from './agent';

export interface Calamity {
  type: CalamityType;
  active: boolean;
}

export * from './simulation';
