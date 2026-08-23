import * as THREE from 'three';
import { Zone, SafeZone } from '../../types/domain';
import { CityRenderer } from '../CityRenderer';

export class ZoneRenderer {
  private renderer: CityRenderer;
  private group: THREE.Group;
  private zoneMeshes: Map<string, THREE.Mesh> = new Map();
  private selectedZoneId: string | null = null;
  private safeZoneIds: Set<string> = new Set();
  
  // Materials
  private normalMaterial = new THREE.MeshBasicMaterial({ color: 0x00aaff, transparent: true, opacity: 0.2, depthWrite: false, side: THREE.DoubleSide });
  private selectedMaterial = new THREE.MeshBasicMaterial({ color: 0xffaa00, transparent: true, opacity: 0.4, depthWrite: false, side: THREE.DoubleSide });
  private safeMaterial = new THREE.MeshBasicMaterial({ color: 0x00ffaa, transparent: true, opacity: 0.3, depthWrite: false, side: THREE.DoubleSide });

  // Border materials
  private borderNormalMaterial = new THREE.LineBasicMaterial({ color: 0x00aaff, linewidth: 2 });
  private borderSelectedMaterial = new THREE.LineBasicMaterial({ color: 0xffaa00, linewidth: 4 });
  private borderSafeMaterial = new THREE.LineBasicMaterial({ color: 0x00ffaa, linewidth: 2 });

  constructor(renderer: CityRenderer) {
    this.renderer = renderer;
    this.group = new THREE.Group();
    this.group.position.y = 2; // slight offset above ground
    this.renderer.addOverlay(this.group);
  }

  public updateZones(zones: Zone[], safeZones: SafeZone[]) {
    this.safeZoneIds = new Set(safeZones.map(sz => sz.zoneId));

    // Remove old zones not in the new list
    const newZoneIds = new Set(zones.map(z => z.id));
    for (const [id, mesh] of this.zoneMeshes.entries()) {
      if (!newZoneIds.has(id)) {
        this.group.remove(mesh);
        this.zoneMeshes.delete(id);
      }
    }

    // Add or update zones
    for (const zone of zones) {
      if (zone.spatial.type === 'unknown' || !zone.spatial.coordinates) continue;

      if (!this.zoneMeshes.has(zone.id)) {
        // Create circle geometry for the zone as a temporary placeholder for points
        const radius = 250;
        const coords = zone.spatial.coordinates;

        const geometry = new THREE.CircleGeometry(radius, 32);
        const mesh = new THREE.Mesh(geometry, this.getMaterialForZone(zone.id));
        mesh.rotation.x = -Math.PI / 2; // Flat on the ground
        mesh.position.set(coords[0], coords[1], coords[2]);
        mesh.userData = { isZone: true, zoneId: zone.id };
        
        // Outline
        const edges = new THREE.EdgesGeometry(geometry);
        const line = new THREE.LineLoop(edges, this.getBorderMaterialForZone(zone.id));
        mesh.add(line);

        this.group.add(mesh);
        this.zoneMeshes.set(zone.id, mesh);
      } else {
        const mesh = this.zoneMeshes.get(zone.id)!;
        mesh.material = this.getMaterialForZone(zone.id);
        const line = mesh.children[0] as THREE.LineLoop;
        line.material = this.getBorderMaterialForZone(zone.id);
      }
    }
  }

  public setSelectedZone(zoneId: string | null) {
    if (this.selectedZoneId === zoneId) return;
    const oldSelected = this.selectedZoneId;
    this.selectedZoneId = zoneId;

    if (oldSelected && this.zoneMeshes.has(oldSelected)) {
      const mesh = this.zoneMeshes.get(oldSelected)!;
      mesh.material = this.getMaterialForZone(oldSelected);
      const line = mesh.children[0] as THREE.LineLoop;
      line.material = this.getBorderMaterialForZone(oldSelected);
    }

    if (this.selectedZoneId && this.zoneMeshes.has(this.selectedZoneId)) {
      const mesh = this.zoneMeshes.get(this.selectedZoneId)!;
      mesh.material = this.getMaterialForZone(this.selectedZoneId);
      const line = mesh.children[0] as THREE.LineLoop;
      line.material = this.getBorderMaterialForZone(this.selectedZoneId);
    }
  }

  private getMaterialForZone(zoneId: string) {
    if (this.selectedZoneId === zoneId) return this.selectedMaterial;
    if (this.safeZoneIds.has(zoneId)) return this.safeMaterial;
    return this.normalMaterial;
  }

  private getBorderMaterialForZone(zoneId: string) {
    if (this.selectedZoneId === zoneId) return this.borderSelectedMaterial;
    if (this.safeZoneIds.has(zoneId)) return this.borderSafeMaterial;
    return this.borderNormalMaterial;
  }

  public getInteractiveObjects(): THREE.Object3D[] {
    return this.group.children;
  }

  public dispose() {
    this.renderer.removeOverlay(this.group);
    
    // Dispose materials
    this.normalMaterial.dispose();
    this.selectedMaterial.dispose();
    this.safeMaterial.dispose();
    this.borderNormalMaterial.dispose();
    this.borderSelectedMaterial.dispose();
    this.borderSafeMaterial.dispose();

    // Dispose geometries
    for (const mesh of this.zoneMeshes.values()) {
      mesh.geometry.dispose();
      const line = mesh.children[0] as THREE.LineLoop;
      if (line) line.geometry.dispose();
    }
    this.zoneMeshes.clear();
  }
}
