import * as THREE from 'three';
import { CityRenderer } from '../CityRenderer';
import { WorldBounds, Point2D } from '../zones/voronoi';
import { useStore } from '../../store';

export type CameraMode = 'orthographic' | 'freecam';

export interface CameraTransitionOptions {
  duration?: number;
  force?: boolean;
  onComplete?: () => void;
}

interface ActiveTransition {
  startMode: CameraMode;
  endMode: CameraMode;
  startPos: THREE.Vector3;
  endPos: THREE.Vector3;
  startTarget: THREE.Vector3;
  endTarget: THREE.Vector3;
  startZoom: number;
  endZoom: number;
  duration: number;
  elapsed: number;
  onComplete?: () => void;
}

/**
 * CameraController — SATARK Phase 5.2 Corrected Two-Mode Camera Architecture.
 *
 * Modes:
 * 1. Orthographic Strategic Mode (THREE.OrthographicCamera)
 *    - Default on startup.
 *    - Frames the terrain footprint landmass centroid and bounds.
 *    - WASD pans camera horizontally on the ground plane (no rotation).
 *    - Mouse scroll zooms orthographic view with min/max clamps.
 *
 * 2. Freecam Perspective Mode (THREE.PerspectiveCamera)
 *    - First-person 3D camera experience for street and building inspection.
 *    - W/S: Horizontal forward/backward movement derived from camera horizontal yaw.
 *    - A/D: Horizontal strafe left/right derived from horizontal perpendicular vector.
 *    - SPACE: Fly upward (+Y).
 *    - CTRL: Fly downward (-Y).
 *    - SHIFT + Mouse Movement: Smooth first-person look (yaw and pitch, clamped -89° to +89°).
 *    - Mouse movement without Shift: No camera rotation.
 *    - Scroll: Smooth forward/backward movement down to the terrain safety limit.
 *    - Terrain Floor Collision: Dynamic raycast ensures camera never clips below terrain floor.
 *
 * 3. Zone-Entry & Transitions:
 *    - Single-clicking a zone transitions directly into low street-level freecam.
 *    - View is nearly horizontal across the city (street inspection, not distant sky overview).
 *    - Clicking another zone while in freecam smoothly repositions close to the new zone.
 *
 * 4. Double-Click Reset:
 *    - Double-clicking anywhere smoothly returns to default orthographic strategic overview.
 */
export class CameraController {
  private renderer: CityRenderer;
  private mode: CameraMode = 'orthographic';
  private unsubscribeTick: () => void;
  private isDisposed = false;

  // Active transition state
  private activeTransition: ActiveTransition | null = null;

  // World bounds for constraints
  private worldBounds: WorldBounds | null = null;
  private panMargin = 1200;
  private freecamMargin = 2200;

  // Input states
  private keys: Record<string, boolean> = {};
  private isShiftDown = false;

  // Freecam orientation (radians)
  private freecamYaw = -Math.PI * 0.25;
  private freecamPitch = -0.05; // Slightly downward (~-3°), nearly horizontal

  // Tuning Constants
  public static readonly ORTHO_PAN_SPEED = 2400; // units / second at zoom 1.0
  public static readonly FREECAM_MOVE_SPEED = 800; // units / second
  public static readonly FREECAM_VERTICAL_SPEED = 600; // units / second (Space / Ctrl)
  public static readonly FREECAM_LOOK_SENSITIVITY = 0.0024;
  public static readonly SAFE_EYE_OFFSET = 8.0; // Street-level eye height above terrain
  public static readonly MIN_ORTHO_ZOOM = 0.65;
  public static readonly MAX_ORTHO_ZOOM = 6.0;
  public static readonly DEFAULT_TRANSITION_DURATION = 0.85;
  public static readonly FAST_TRANSITION_DURATION = 0.55;
  public static readonly MAX_PITCH = (89 * Math.PI) / 180; // 89 degrees
  public static readonly FREECAM_COLLISION_DISTANCE = 12.0; // Min distance from solid geometry (buildings)
  public static readonly FREECAM_COLLISION_PROBE_RANGE = 80.0; // Max raycast distance to scan ahead for geometry

  constructor(renderer: CityRenderer) {
    this.renderer = renderer;

    // Subscribe to existing CityRenderer animation frame tick
    this.unsubscribeTick = this.renderer.onTick((delta) => {
      this.tick(delta);
    });

    // Window / custom event listeners
    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('keyup', this.handleKeyUp);
    window.addEventListener('mousemove', this.handleMouseMove);
    window.addEventListener('wheel', this.handleWheel, { passive: false });
    window.addEventListener('blur', this.handleWindowBlur);
    document.addEventListener('visibilitychange', this.handleVisibilityChange);

    window.addEventListener('satark:camera-focus-zone', this.handleFocusEvent);
    window.addEventListener('satark:camera-reset-overview', this.handleResetOverviewEvent);
  }

  // ────────────────────────────────────────────────────────────
  // Mode & State Getters
  // ────────────────────────────────────────────────────────────

  public getMode(): CameraMode {
    return this.mode;
  }

  private isInputFocused(): boolean {
    const activeEl = document.activeElement;
    if (!activeEl) return false;
    const tag = activeEl.tagName.toLowerCase();
    return (
      tag === 'input' ||
      tag === 'textarea' ||
      tag === 'select' ||
      (activeEl as HTMLElement).isContentEditable
    );
  }

  // ────────────────────────────────────────────────────────────
  // Event Handlers (Keyboard, Mouse Look, Scroll)
  // ────────────────────────────────────────────────────────────

  private handleKeyDown = (e: KeyboardEvent) => {
    if (this.isDisposed || this.isInputFocused()) return;

    this.keys[e.code] = true;
    if (e.key === 'Shift' || e.code === 'ShiftLeft' || e.code === 'ShiftRight') {
      this.isShiftDown = true;
    }
  };

  private handleKeyUp = (e: KeyboardEvent) => {
    if (this.isDisposed) return;

    this.keys[e.code] = false;
    if (e.key === 'Shift' || e.code === 'ShiftLeft' || e.code === 'ShiftRight') {
      this.isShiftDown = false;
    }
  };

  private handleWindowBlur = () => {
    this.keys = {};
    this.isShiftDown = false;
  };

  private handleVisibilityChange = () => {
    if (document.hidden) {
      this.keys = {};
      this.isShiftDown = false;
    }
  };

  private handleMouseMove = (e: MouseEvent) => {
    if (this.isDisposed || this.activeTransition) return;

    // Shift + Mouse movement looks around ONLY in freecam mode
    // Normal mouse movement WITHOUT Shift MUST NOT rotate the camera
    if (this.mode === 'freecam' && (this.isShiftDown || e.shiftKey)) {
      const dx = e.movementX || 0;
      const dy = e.movementY || 0;

      this.freecamYaw -= dx * CameraController.FREECAM_LOOK_SENSITIVITY;
      this.freecamPitch -= dy * CameraController.FREECAM_LOOK_SENSITIVITY;

      // Clamp pitch to -89° .. +89° to prevent flipping
      this.freecamPitch = Math.max(
        -CameraController.MAX_PITCH,
        Math.min(CameraController.MAX_PITCH, this.freecamPitch)
      );

      const perspCam = this.renderer.getPerspectiveCamera();
      perspCam.rotation.set(this.freecamPitch, this.freecamYaw, 0, 'YXZ');
    }
  };

  private handleWheel = (e: WheelEvent) => {
    if (this.isDisposed || this.activeTransition) return;

    // Only process wheel events if hovering canvas or container
    const target = e.target as HTMLElement | null;
    if (!target || !target.closest('.city-scene-container, canvas')) {
      return;
    }

    if (this.mode === 'orthographic') {
      // Orthographic zoom
      e.preventDefault();
      const orthoCam = this.renderer.getOrthographicCamera();
      const zoomFactor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
      const newZoom = Math.max(
        CameraController.MIN_ORTHO_ZOOM,
        Math.min(CameraController.MAX_ORTHO_ZOOM, orthoCam.zoom * zoomFactor)
      );
      orthoCam.zoom = newZoom;
      orthoCam.updateProjectionMatrix();
    } else if (this.mode === 'freecam') {
      // Freecam forward/backward scroll along camera look vector with collision probing
      e.preventDefault();
      const perspCam = this.renderer.getPerspectiveCamera();
      const lookDir = new THREE.Vector3();
      perspCam.getWorldDirection(lookDir);

      const scrollForward = e.deltaY < 0;
      const moveAmount = scrollForward ? 60 : -60;
      const moveDir = lookDir.clone().multiplyScalar(scrollForward ? 1 : -1);

      // Probe for geometry collision in scroll direction
      const hit = this.renderer.raycastCollision(
        perspCam.position,
        moveDir,
        CameraController.FREECAM_COLLISION_PROBE_RANGE
      );

      if (hit && scrollForward) {
        // If moving toward geometry, clamp at collision distance
        const safeDistance = hit.distance - CameraController.FREECAM_COLLISION_DISTANCE;
        if (safeDistance <= 0) {
          // Already at or past collision distance, don't move forward
          return;
        }
        const clampedAmount = Math.min(Math.abs(moveAmount), safeDistance);
        const newPos = perspCam.position.clone().addScaledVector(lookDir, clampedAmount);
        this.clampFreecamPosition(newPos);
        perspCam.position.copy(newPos);
      } else {
        const newPos = perspCam.position.clone().addScaledVector(lookDir, moveAmount);
        this.clampFreecamPosition(newPos);
        perspCam.position.copy(newPos);
      }
    }
  };

  private handleFocusEvent = (e: Event) => {
    const customEvent = e as CustomEvent<{ zoneId: string; force?: boolean }>;
    if (customEvent.detail?.zoneId) {
      this.focusOnZone(customEvent.detail.zoneId, { force: customEvent.detail.force ?? true });
    }
  };

  private handleResetOverviewEvent = () => {
    this.returnToOrthographic();
  };

  // ────────────────────────────────────────────────────────────
  // Bounds Configuration
  // ────────────────────────────────────────────────────────────

  public setWorldBounds(bounds: WorldBounds): void {
    this.worldBounds = bounds;
    const spanX = Math.abs(bounds.xMax - bounds.xMin);
    const spanZ = Math.abs(bounds.zMax - bounds.zMin);
    const maxSpan = Math.max(spanX, spanZ);
    this.panMargin = maxSpan * 0.25;
    // Generous global boundary: freecam can explore the whole city, all 21 zones, and surrounding ocean
    this.freecamMargin = maxSpan * 2.5;
  }

  public setTerrainFootprint(footprint: Point2D[]): void {
    if (footprint.length === 0) return;
    let minX = Infinity;
    let maxX = -Infinity;
    let minZ = Infinity;
    let maxZ = -Infinity;

    for (const p of footprint) {
      if (p.x < minX) minX = p.x;
      if (p.x > maxX) maxX = p.x;
      if (p.z < minZ) minZ = p.z;
      if (p.z > maxZ) maxZ = p.z;
    }

    this.worldBounds = { xMin: minX, xMax: maxX, zMin: minZ, zMax: maxZ };
    const spanX = maxX - minX;
    const spanZ = maxZ - minZ;
    const maxSpan = Math.max(spanX, spanZ);
    this.panMargin = maxSpan * 0.25;
    // Generous global boundary: freecam can explore the whole city, all 21 zones, and surrounding ocean
    this.freecamMargin = maxSpan * 2.5;
  }

  // ────────────────────────────────────────────────────────────
  // Zone Focus & Freecam Entry (Street-Level Close Positioning)
  // ────────────────────────────────────────────────────────────

  /**
   * Focuses on a zone by ID:
   * - Selects the zone.
   * - Smoothly transitions into low street-level FREECAM.
   * - Positioned at eye-level above terrain, view nearly parallel to ground.
   * - Once transition finishes, user has full unconstrained FPS control.
   */
  public focusOnZone(zoneId: string, options: CameraTransitionOptions = {}): void {
    if (this.isDisposed) return;

    const state = useStore.getState();
    const zone = state.zones.find((z) => z.id === zoneId);
    if (!zone || !zone.center_world) {
      console.warn(`CameraController: Zone ${zoneId} not found or missing center_world.`);
      return;
    }

    const targetX = zone.center_world.x;
    const targetZ = zone.center_world.z;
    const targetTerrainY = this.renderer.getTerrainHeightAt(targetX, targetZ);
    const endTarget = new THREE.Vector3(
      targetX,
      targetTerrainY + CameraController.SAFE_EYE_OFFSET,
      targetZ
    );

    // Low street-level inspection offset (distance ~45 units, eye-level above terrain)
    const offsetX = -32;
    const offsetZ = 32;
    const camX = targetX + offsetX;
    const camZ = targetZ + offsetZ;
    const camTerrainY = this.renderer.getTerrainHeightAt(camX, camZ);
    const camY = camTerrainY + CameraController.SAFE_EYE_OFFSET + 2.0;
    const endPos = new THREE.Vector3(camX, camY, camZ);

    const startMode = this.mode;
    const endMode: CameraMode = 'freecam';

    const currentPos = this.renderer.getCameraPosition();
    const currentTarget = this.mode === 'orthographic'
      ? this.renderer.getControlsTarget()
      : this.getPerspectiveLookTarget();
    const orthoCam = this.renderer.getOrthographicCamera();
    const startZoom = orthoCam.zoom;

    const duration = options.duration ?? (
      this.mode === 'freecam'
        ? CameraController.FAST_TRANSITION_DURATION
        : CameraController.DEFAULT_TRANSITION_DURATION
    );

    this.startTransition({
      startMode,
      endMode,
      startPos: currentPos,
      endPos,
      startTarget: currentTarget.clone(),
      endTarget,
      startZoom,
      endZoom: 1.0,
      duration,
      onComplete: () => {
        // Sync freecam orientation angles to look towards street target
        const lookDir = new THREE.Vector3().subVectors(endTarget, endPos).normalize();
        this.freecamYaw = Math.atan2(-lookDir.x, -lookDir.z);
        this.freecamPitch = Math.asin(Math.max(-0.95, Math.min(0.95, lookDir.y)));
        const perspCam = this.renderer.getPerspectiveCamera();
        perspCam.rotation.set(this.freecamPitch, this.freecamYaw, 0, 'YXZ');
        options.onComplete?.();
      },
    });
  }

  /**
   * Enters freecam at a specific hit point on the map/terrain at street level.
   */
  public enterFreecamAt(hitPoint: THREE.Vector3, options: CameraTransitionOptions = {}): void {
    if (this.isDisposed) return;

    const targetX = hitPoint.x;
    const targetZ = hitPoint.z;
    const targetTerrainY = this.renderer.getTerrainHeightAt(targetX, targetZ, hitPoint.y);
    const endTarget = new THREE.Vector3(
      targetX,
      targetTerrainY + CameraController.SAFE_EYE_OFFSET,
      targetZ
    );

    const offsetX = -30;
    const offsetZ = 30;
    const camX = targetX + offsetX;
    const camZ = targetZ + offsetZ;
    const camTerrainY = this.renderer.getTerrainHeightAt(camX, camZ, targetTerrainY);
    const camY = camTerrainY + CameraController.SAFE_EYE_OFFSET + 2.0;
    const endPos = new THREE.Vector3(camX, camY, camZ);

    const startMode = this.mode;
    const endMode: CameraMode = 'freecam';

    const currentPos = this.renderer.getCameraPosition();
    const currentTarget = this.mode === 'orthographic'
      ? this.renderer.getControlsTarget()
      : this.getPerspectiveLookTarget();
    const orthoCam = this.renderer.getOrthographicCamera();
    const startZoom = orthoCam.zoom;

    const duration = options.duration ?? CameraController.DEFAULT_TRANSITION_DURATION;

    this.startTransition({
      startMode,
      endMode,
      startPos: currentPos,
      endPos,
      startTarget: currentTarget.clone(),
      endTarget,
      startZoom,
      endZoom: 1.0,
      duration,
      onComplete: () => {
        const lookDir = new THREE.Vector3().subVectors(endTarget, endPos).normalize();
        this.freecamYaw = Math.atan2(-lookDir.x, -lookDir.z);
        this.freecamPitch = Math.asin(Math.max(-0.95, Math.min(0.95, lookDir.y)));
        const perspCam = this.renderer.getPerspectiveCamera();
        perspCam.rotation.set(this.freecamPitch, this.freecamYaw, 0, 'YXZ');
        options.onComplete?.();
      },
    });
  }

  /**
   * Enters freecam preserving current camera position and direction.
   */
  public enterFreecam(): void {
    if (this.isDisposed || this.mode === 'freecam') return;

    const orthoCam = this.renderer.getOrthographicCamera();
    const perspCam = this.renderer.getPerspectiveCamera();
    const target = this.renderer.getControlsTarget();

    perspCam.position.copy(orthoCam.position);
    perspCam.lookAt(target);

    const lookDir = new THREE.Vector3();
    perspCam.getWorldDirection(lookDir);
    this.freecamYaw = Math.atan2(-lookDir.x, -lookDir.z);
    this.freecamPitch = Math.asin(Math.max(-0.95, Math.min(0.95, lookDir.y)));
    perspCam.rotation.set(this.freecamPitch, this.freecamYaw, 0, 'YXZ');

    this.mode = 'freecam';
    this.renderer.setCameraMode('freecam');
  }

  // ────────────────────────────────────────────────────────────
  // Reset / Return to Default Orthographic Overview
  // ────────────────────────────────────────────────────────────

  /**
   * Smoothly returns to default orthographic strategic overview.
   */
  public returnToOrthographic(options: CameraTransitionOptions = {}): void {
    if (this.isDisposed) return;

    const defaultView = this.renderer.getDefaultView();
    if (!defaultView) {
      console.warn('CameraController: Default view parameters not yet available.');
      return;
    }

    const currentPos = this.renderer.getCameraPosition();
    const currentTarget = this.mode === 'orthographic'
      ? this.renderer.getControlsTarget()
      : this.getPerspectiveLookTarget();

    const orthoCam = this.renderer.getOrthographicCamera();
    const startZoom = orthoCam.zoom;

    const duration = options.duration ?? CameraController.DEFAULT_TRANSITION_DURATION;

    this.startTransition({
      startMode: this.mode,
      endMode: 'orthographic',
      startPos: currentPos,
      endPos: defaultView.position,
      startTarget: currentTarget,
      endTarget: defaultView.target,
      startZoom,
      endZoom: 1.0,
      duration,
      onComplete: () => {
        orthoCam.zoom = 1.0;
        this.renderer.updateOrthographicFrustum();
        this.renderer.setControlsTarget(defaultView.target.x, defaultView.target.y, defaultView.target.z);
        this.renderer.updateControls();
        options.onComplete?.();
      },
    });
  }

  public resetToOverview(options: CameraTransitionOptions = {}): void {
    this.returnToOrthographic(options);
  }

  private getPerspectiveLookTarget(): THREE.Vector3 {
    const perspCam = this.renderer.getPerspectiveCamera();
    const lookDir = new THREE.Vector3();
    perspCam.getWorldDirection(lookDir);
    return perspCam.position.clone().addScaledVector(lookDir, 1000);
  }

  // ────────────────────────────────────────────────────────────
  // Smooth Transition Engine
  // ────────────────────────────────────────────────────────────

  private startTransition(params: {
    startMode: CameraMode;
    endMode: CameraMode;
    startPos: THREE.Vector3;
    endPos: THREE.Vector3;
    startTarget: THREE.Vector3;
    endTarget: THREE.Vector3;
    startZoom: number;
    endZoom: number;
    duration: number;
    onComplete?: () => void;
  }): void {
    // If start and end are practically identical, switch mode immediately
    if (
      params.startMode === params.endMode &&
      params.startPos.distanceTo(params.endPos) < 1.0 &&
      params.startTarget.distanceTo(params.endTarget) < 1.0
    ) {
      this.renderer.setCameraPosition(params.endPos.x, params.endPos.y, params.endPos.z);
      this.renderer.setControlsTarget(params.endTarget.x, params.endTarget.y, params.endTarget.z);
      this.renderer.updateControls();
      params.onComplete?.();
      return;
    }

    // Set mode at beginning of transition to destination camera
    this.mode = params.endMode;
    this.renderer.setCameraMode(params.endMode);

    this.activeTransition = {
      startMode: params.startMode,
      endMode: params.endMode,
      startPos: params.startPos.clone(),
      endPos: params.endPos.clone(),
      startTarget: params.startTarget.clone(),
      endTarget: params.endTarget.clone(),
      startZoom: params.startZoom,
      endZoom: params.endZoom,
      duration: Math.max(params.duration, 0.1),
      elapsed: 0,
      onComplete: params.onComplete,
    };
  }

  private easeInOutCubic(t: number): number {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  // ────────────────────────────────────────────────────────────
  // Main Animation Frame Tick
  // ────────────────────────────────────────────────────────────

  private tick(delta: number): void {
    if (this.isDisposed) return;

    // 1. Process active camera transition
    if (this.activeTransition) {
      const trans = this.activeTransition;
      trans.elapsed += delta;
      const progress = Math.min(trans.elapsed / trans.duration, 1.0);
      const eased = this.easeInOutCubic(progress);

      const curPos = new THREE.Vector3().lerpVectors(trans.startPos, trans.endPos, eased);
      const curTarget = new THREE.Vector3().lerpVectors(trans.startTarget, trans.endTarget, eased);

      const activeCam = this.renderer.getActiveCamera();
      activeCam.position.copy(curPos);
      activeCam.lookAt(curTarget);
      activeCam.updateMatrixWorld(true);

      if (trans.endMode === 'orthographic') {
        const orthoCam = this.renderer.getOrthographicCamera();
        orthoCam.zoom = THREE.MathUtils.lerp(trans.startZoom, trans.endZoom, eased);
        orthoCam.updateProjectionMatrix();
        this.renderer.setControlsTarget(curTarget.x, curTarget.y, curTarget.z);
        this.renderer.updateControls();
      }

      if (progress >= 1.0) {
        const onComplete = trans.onComplete;
        this.activeTransition = null;

        activeCam.position.copy(trans.endPos);
        activeCam.lookAt(trans.endTarget);
        activeCam.updateMatrixWorld(true);

        if (trans.endMode === 'orthographic') {
          const orthoCam = this.renderer.getOrthographicCamera();
          orthoCam.zoom = trans.endZoom;
          orthoCam.updateProjectionMatrix();
          this.renderer.setControlsTarget(trans.endTarget.x, trans.endTarget.y, trans.endTarget.z);
          this.renderer.updateControls();
        }

        onComplete?.();
      }
      return;
    }

    // 2. Handle WASD & continuous controls when no transition is active
    if (this.mode === 'orthographic') {
      this.updateOrthographicWASD(delta);
    } else if (this.mode === 'freecam') {
      this.updateFreecamMovement(delta);
    }
  }

  // ────────────────────────────────────────────────────────────
  // Orthographic Mode WASD Panning
  // ────────────────────────────────────────────────────────────

  private updateOrthographicWASD(delta: number): void {
    if (this.isInputFocused()) return;

    const orthoCam = this.renderer.getOrthographicCamera();

    // Compute forward and right vectors along ground plane
    const forward = new THREE.Vector3();
    orthoCam.getWorldDirection(forward);
    forward.y = 0;
    forward.normalize();

    const right = new THREE.Vector3().crossVectors(forward, new THREE.Vector3(0, 1, 0)).normalize();

    const panVec = new THREE.Vector3();
    if (this.keys['KeyW'] || this.keys['ArrowUp']) panVec.add(forward);
    if (this.keys['KeyS'] || this.keys['ArrowDown']) panVec.sub(forward);
    if (this.keys['KeyD'] || this.keys['ArrowRight']) panVec.add(right);
    if (this.keys['KeyA'] || this.keys['ArrowLeft']) panVec.sub(right);

    if (panVec.lengthSq() > 0) {
      panVec.normalize();
      const panSpeed = (CameraController.ORTHO_PAN_SPEED / orthoCam.zoom) * delta;

      const currentPos = orthoCam.position.clone();
      const currentTarget = this.renderer.getControlsTarget();

      currentPos.addScaledVector(panVec, panSpeed);
      currentTarget.addScaledVector(panVec, panSpeed);

      this.clampOrthographicPositionAndTarget(currentPos, currentTarget);

      orthoCam.position.copy(currentPos);
      this.renderer.setControlsTarget(currentTarget.x, currentTarget.y, currentTarget.z);
      this.renderer.updateControls();
    }
  }

  private clampOrthographicPositionAndTarget(pos: THREE.Vector3, target: THREE.Vector3): void {
    if (!this.worldBounds) return;

    const minX = this.worldBounds.xMin - this.panMargin;
    const maxX = this.worldBounds.xMax + this.panMargin;
    const minZ = this.worldBounds.zMin - this.panMargin;
    const maxZ = this.worldBounds.zMax + this.panMargin;

    const offset = pos.clone().sub(target);

    if (target.x < minX) target.x = minX;
    else if (target.x > maxX) target.x = maxX;

    if (target.z < minZ) target.z = minZ;
    else if (target.z > maxZ) target.z = maxZ;

    pos.copy(target).add(offset);
  }

  // ────────────────────────────────────────────────────────────
  // Freecam Mode True FPS WASD & Vertical Movement
  // ────────────────────────────────────────────────────────────

  private updateFreecamMovement(delta: number): void {
    if (this.isInputFocused()) return;

    const perspCam = this.renderer.getPerspectiveCamera();

    // 1. Planar horizontal movement (XZ) derived solely from horizontal yaw
    // Looking up/down (pitch) does NOT cause forward/backward movement to dive into ground/sky
    const forward = new THREE.Vector3(-Math.sin(this.freecamYaw), 0, -Math.cos(this.freecamYaw)).normalize();
    const right = new THREE.Vector3(Math.cos(this.freecamYaw), 0, -Math.sin(this.freecamYaw)).normalize();

    const horizontalMove = new THREE.Vector3();
    if (this.keys['KeyW'] || this.keys['ArrowUp']) horizontalMove.add(forward);
    if (this.keys['KeyS'] || this.keys['ArrowDown']) horizontalMove.sub(forward);
    if (this.keys['KeyD'] || this.keys['ArrowRight']) horizontalMove.add(right);
    if (this.keys['KeyA'] || this.keys['ArrowLeft']) horizontalMove.sub(right);

    // 2. Vertical movement independent of look orientation (SPACE = up, CTRL = down)
    let verticalMove = 0;
    if (this.keys['Space']) {
      verticalMove += 1;
    }
    if (this.keys['ControlLeft'] || this.keys['ControlRight']) {
      verticalMove -= 1;
    }

    const hasHorizontal = horizontalMove.lengthSq() > 0;
    const hasVertical = verticalMove !== 0;

    if (hasHorizontal || hasVertical) {
      const newPos = perspCam.position.clone();
      const currentPos = perspCam.position;

      if (hasHorizontal) {
        horizontalMove.normalize();
        const moveSpeed = CameraController.FREECAM_MOVE_SPEED * delta;

        // Probe for collision in the horizontal movement direction
        const collisionClamped = this.probeMovementCollision(
          currentPos,
          horizontalMove,
          moveSpeed
        );
        newPos.add(collisionClamped);
      }

      if (hasVertical) {
        const vertSpeed = CameraController.FREECAM_VERTICAL_SPEED * delta;
        const vertDir = new THREE.Vector3(0, verticalMove > 0 ? 1 : -1, 0);

        // Probe vertical collision (mostly relevant for descending into geometry)
        const collisionClamped = this.probeMovementCollision(
          currentPos,
          vertDir,
          vertSpeed
        );
        newPos.add(collisionClamped);
      }

      this.clampFreecamPosition(newPos);
      perspCam.position.copy(newPos);
    }
  }

  /**
   * Probes for geometry collision along a movement direction.
   * Returns the safe displacement vector (clamped if collision detected).
   * Does NOT depend on any zone — uses only global scene geometry.
   */
  private probeMovementCollision(
    origin: THREE.Vector3,
    direction: THREE.Vector3,
    desiredDistance: number
  ): THREE.Vector3 {
    const normalizedDir = direction.clone().normalize();

    const hit = this.renderer.raycastCollision(
      origin,
      normalizedDir,
      CameraController.FREECAM_COLLISION_PROBE_RANGE
    );

    if (hit) {
      const safeDistance = hit.distance - CameraController.FREECAM_COLLISION_DISTANCE;
      if (safeDistance <= 0) {
        // Already within or at the collision boundary — no movement in this direction
        return new THREE.Vector3(0, 0, 0);
      }
      // Clamp to safe distance if desired movement would exceed it
      const actualDistance = Math.min(desiredDistance, safeDistance);
      return normalizedDir.multiplyScalar(actualDistance);
    }

    // No collision — full movement
    return normalizedDir.multiplyScalar(desiredDistance);
  }

  /**
   * Enforces terrain floor collision (camera never clips below terrain floor)
   * and generous world boundaries.
   */
  private clampFreecamPosition(pos: THREE.Vector3): void {
    // Dynamic raycast terrain height lookup
    const localTerrainY = this.renderer.getTerrainHeightAt(pos.x, pos.z);
    const minY = localTerrainY + CameraController.SAFE_EYE_OFFSET;
    const maxY = localTerrainY + 50000; // Generous global altitude ceiling

    if (pos.y < minY) pos.y = minY;
    if (pos.y > maxY) pos.y = maxY;

    if (this.worldBounds) {
      const minX = this.worldBounds.xMin - this.freecamMargin;
      const maxX = this.worldBounds.xMax + this.freecamMargin;
      const minZ = this.worldBounds.zMin - this.freecamMargin;
      const maxZ = this.worldBounds.zMax + this.freecamMargin;

      if (pos.x < minX) pos.x = minX;
      else if (pos.x > maxX) pos.x = maxX;
      if (pos.z < minZ) pos.z = minZ;
      else if (pos.z > maxZ) pos.z = maxZ;
    }
  }

  // ────────────────────────────────────────────────────────────
  // Disposal
  // ────────────────────────────────────────────────────────────

  public dispose(): void {
    this.isDisposed = true;
    this.activeTransition = null;

    window.removeEventListener('keydown', this.handleKeyDown);
    window.removeEventListener('keyup', this.handleKeyUp);
    window.removeEventListener('mousemove', this.handleMouseMove);
    window.removeEventListener('wheel', this.handleWheel);
    window.removeEventListener('blur', this.handleWindowBlur);
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);

    window.removeEventListener('satark:camera-focus-zone', this.handleFocusEvent);
    window.removeEventListener('satark:camera-reset-overview', this.handleResetOverviewEvent);

    this.unsubscribeTick();
  }
}
