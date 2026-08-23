import * as THREE from 'three';
import { Calamity } from '../../types/domain';
import { FloodRenderer } from './flood/FloodRenderer';
import { EarthquakeRenderer } from './earthquake/EarthquakeRenderer';

export class DisasterRenderer {
  private floodRenderer: FloodRenderer;
  private earthquakeRenderer: EarthquakeRenderer;

  constructor(scene: THREE.Scene) {
    this.floodRenderer = new FloodRenderer(scene);
    this.earthquakeRenderer = new EarthquakeRenderer(scene);
  }

  public updateCalamity(calamity: Calamity | null) {
    // Reset all renderers first
    this.floodRenderer.clear();
    this.earthquakeRenderer.clear();

    if (!calamity) return;

    if (calamity.type === 'Flood') {
      this.floodRenderer.render(calamity);
    } else if (calamity.type === 'Earthquake') {
      this.earthquakeRenderer.render(calamity);
    }
  }

  public clear() {
    this.updateCalamity(null);
  }

  public dispose() {
    this.floodRenderer.dispose();
    this.earthquakeRenderer.dispose();
  }
}

