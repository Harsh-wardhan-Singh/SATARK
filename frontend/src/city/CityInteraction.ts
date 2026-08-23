import * as THREE from 'three';
import { useStore } from '../store';
import { CityRenderer } from './CityRenderer';
import { ZoneRenderer } from './zones/ZoneRenderer';
import { CameraController } from './camera/CameraController';

export class CityInteraction {
  private mouse = new THREE.Vector2();
  private container: HTMLElement;
  private renderer: CityRenderer;
  private zoneRenderer: ZoneRenderer;
  private cameraController: CameraController;

  private clickTimeout: number | null = null;
  private lastClickTime = 0;
  private readonly DOUBLE_CLICK_DELAY = 220; // ms

  constructor(
    container: HTMLElement,
    renderer: CityRenderer,
    zoneRenderer: ZoneRenderer,
    cameraController: CameraController
  ) {
    this.container = container;
    this.renderer = renderer;
    this.zoneRenderer = zoneRenderer;
    this.cameraController = cameraController;

    this.container.addEventListener('click', this.onClick);
    this.container.addEventListener('dblclick', this.onDoubleClick);
  }

  private onClick = (event: MouseEvent) => {
    // Only handle primary left clicks
    if (event.button !== 0) return;

    const now = performance.now();
    const timeSinceLastClick = now - this.lastClickTime;
    this.lastClickTime = now;

    // If second click arrived within the double click window, cancel single click
    if (timeSinceLastClick < this.DOUBLE_CLICK_DELAY || this.clickTimeout !== null) {
      if (this.clickTimeout !== null) {
        window.clearTimeout(this.clickTimeout);
        this.clickTimeout = null;
      }
      this.handleDoubleClick();
      return;
    }

    // Schedule single click execution after discrimination debounce
    this.clickTimeout = window.setTimeout(() => {
      this.clickTimeout = null;
      this.handleSingleClick(event);
    }, this.DOUBLE_CLICK_DELAY);
  };

  private onDoubleClick = (event: MouseEvent) => {
    if (event.button !== 0) return;
    if (this.clickTimeout !== null) {
      window.clearTimeout(this.clickTimeout);
      this.clickTimeout = null;
    }
    this.handleDoubleClick();
  };

  private handleSingleClick(event: MouseEvent) {
    const rect = this.container.getBoundingClientRect();
    this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    // 1. Raycast interactive zones
    const interactiveObjects = this.zoneRenderer.getInteractiveObjects();
    const intersects = this.renderer.raycast(this.mouse, interactiveObjects);

    if (intersects.length > 0) {
      const validIntersection = intersects.find(
        (intersect) => intersect.object.userData && intersect.object.userData.isZone
      );
      if (validIntersection) {
        const selectedZoneId = validIntersection.object.userData.zoneId;
        useStore.getState().setSelectedZoneId(selectedZoneId);
        this.cameraController.focusOnZone(selectedZoneId);
        return;
      }
    }

    // 2. Clicked outside zones: deselect zone
    useStore.getState().setSelectedZoneId(null);

    // 3. Raycast terrain for precise freecam focus position
    const terrainIntersects = this.renderer.raycastTerrain(this.mouse);
    if (terrainIntersects.length > 0 && terrainIntersects[0].point) {
      this.cameraController.enterFreecamAt(terrainIntersects[0].point);
    } else {
      this.cameraController.enterFreecam();
    }
  }

  private handleDoubleClick() {
    // Clear zone selection and return to orthographic overview
    useStore.getState().setSelectedZoneId(null);
    this.cameraController.returnToOrthographic();
  }

  public dispose() {
    if (this.clickTimeout !== null) {
      window.clearTimeout(this.clickTimeout);
      this.clickTimeout = null;
    }
    this.container.removeEventListener('click', this.onClick);
    this.container.removeEventListener('dblclick', this.onDoubleClick);
  }
}
