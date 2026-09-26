export type CalamityType = 'FLOOD';

export interface WorldCoordinate {
  x: number;
  z: number;
}

export interface NormalizedCoordinate {
  x: number;
  y: number;
}

export interface GeoCoordinate {
  lat: number;
  lng: number;
}

export interface Zone {
  id: string;
  name?: string;
  center_world: WorldCoordinate;
  center_normalized?: NormalizedCoordinate;
  coordinates?: GeoCoordinate;
  neighbors: string[];
  elevation?: number;
  ward_code?: string;
  ward_name?: string;
  risk_classification?: string;
  primary_land_use?: string;
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

export interface FloodEnvironment {
  flood_water_levels: Record<string, number>;
  rainfall_intensity: number;
  drainage?: any;
  risk?: any;
  decision?: any;
  subsystems?: any;
  intervention?: any;
}

export * from './simulation';
