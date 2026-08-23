import * as THREE from 'three';
import { useStore } from '../store';
import { CityRenderer } from './CityRenderer';
import { ZoneRenderer } from './zones/ZoneRenderer';

export class CityInteraction {
  private mouse = new THREE.Vector2();
  private container: HTMLElement;
  private renderer: CityRenderer;
  private zoneRenderer: ZoneRenderer;

  constructor(container: HTMLElement, renderer: CityRenderer, zoneRenderer: ZoneRenderer) {
    this.container = container;
    this.renderer = renderer;
    this.zoneRenderer = zoneRenderer;

    this.onClick = this.onClick.bind(this);
    this.container.addEventListener('click', this.onClick);
  }

  private onClick(event: MouseEvent) {
    // Only handle left clicks
    if (event.button !== 0) return;

    const rect = this.container.getBoundingClientRect();
    this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    const interactiveObjects = this.zoneRenderer.getInteractiveObjects();
    const intersects = this.renderer.raycast(this.mouse, interactiveObjects);

    if (intersects.length > 0) {
      // Find the first valid zone intersection
      const validIntersection = intersects.find(intersect => intersect.object.userData && intersect.object.userData.isZone);
      if (validIntersection) {
        const selectedZoneId = validIntersection.object.userData.zoneId;
        useStore.getState().setSelectedZoneId(selectedZoneId);
        return;
      }
    }
    
    // If clicking on empty space or building, deselect
    useStore.getState().setSelectedZoneId(null);
  }

  public dispose() {
    this.container.removeEventListener('click', this.onClick);
  }
}
