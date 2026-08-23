import { useStore, StoreState } from '../store';
import { ZoneRenderer } from './zones/ZoneRenderer';
import { AgentRenderer } from './agents/AgentRenderer';
import { CameraController } from './camera/CameraController';

export class CityStateAdapter {
  private zoneRenderer: ZoneRenderer;
  private agentRenderer?: AgentRenderer;
  private cameraController?: CameraController;
  private unsubscribeWorld: () => void;
  private unsubscribeUi: () => void;
  private unsubscribeAgents?: () => void;
  private lastSelectedZoneId: string | null = null;

  constructor(
    zoneRenderer: ZoneRenderer,
    agentRenderer?: AgentRenderer,
    cameraController?: CameraController
  ) {
    this.zoneRenderer = zoneRenderer;
    this.agentRenderer = agentRenderer;
    this.cameraController = cameraController;

    // Listen to world state changes
    this.unsubscribeWorld = useStore.subscribe(
      (state: StoreState) => {
        this.zoneRenderer.updateZones(state.zones, state.safeZones);
      }
    );

    // Listen to UI state changes
    this.lastSelectedZoneId = useStore.getState().selectedZoneId;
    this.unsubscribeUi = useStore.subscribe(
      (state: StoreState) => {
        const newSelectedZoneId = state.selectedZoneId;
        if (newSelectedZoneId !== this.lastSelectedZoneId) {
          this.lastSelectedZoneId = newSelectedZoneId;
          this.zoneRenderer.setSelectedZone(newSelectedZoneId);
          if (newSelectedZoneId) {
            this.cameraController?.focusOnZone(newSelectedZoneId);
          }
        }
      }
    );

    // Listen to Agent state changes
    if (this.agentRenderer) {
      this.unsubscribeAgents = useStore.subscribe(
        (state: StoreState) => {
          this.agentRenderer?.updateAgents(Object.values(state.agents));
        }
      );
    }

    // Initial sync
    const state = useStore.getState();
    this.zoneRenderer.updateZones(state.zones, state.safeZones);
    this.zoneRenderer.setSelectedZone(state.selectedZoneId);
    if (this.agentRenderer) {
      this.agentRenderer.updateAgents(Object.values(state.agents));
    }
  }

  public dispose() {
    this.unsubscribeWorld();
    this.unsubscribeUi();
    if (this.unsubscribeAgents) {
      this.unsubscribeAgents();
    }
  }
}


