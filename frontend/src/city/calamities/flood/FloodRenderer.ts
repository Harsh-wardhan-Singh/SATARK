import * as THREE from 'three';
import { Calamity } from '../../../types/domain';

export class FloodRenderer {
  constructor(_scene: THREE.Scene) {
    // Save scene for later when implementation is done
  }

  public render(_calamity: Calamity) {
    // Phase 6B: Foundation only. Do not invent flood visuals here.
    // This is an extension point for when the backend authoritative flood state is ready.
  }

  public clear() {
    // Remove any visual elements
  }

  public dispose() {
    this.clear();
  }
}

