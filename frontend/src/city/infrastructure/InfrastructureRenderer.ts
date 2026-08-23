import * as THREE from 'three';

export class InfrastructureRenderer {
  constructor(_scene: THREE.Scene) {
    // Save scene for later when implementation is done
  }

  public updateInfrastructure(_data: any) {
    // Phase 6B: Foundation only. Do not invent infrastructure visuals here.
    // This is an extension point for when the backend authoritative infrastructure state is ready.
  }

  public clear() {
    // Remove any visual elements
  }

  public dispose() {
    this.clear();
  }
}

