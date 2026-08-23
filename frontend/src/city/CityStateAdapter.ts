import { useStore, StoreState } from '../store';
import { ZoneRenderer } from './zones/ZoneRenderer';
import { AgentRenderer } from './agents/AgentRenderer';
import { CameraController } from './camera/CameraController';
import { DisasterRenderer } from './calamities/DisasterRenderer';
import { InfrastructureRenderer } from './infrastructure/InfrastructureRenderer';

export class CityStateAdapter {
  private zoneRenderer: ZoneRenderer;
  private agentRenderer?: AgentRenderer;
  private cameraController?: CameraController;
  private disasterRenderer?: DisasterRenderer;
  private infrastructureRenderer?: InfrastructureRenderer;
  
  private unsubscribeWorld: () => void;
  private unsubscribeUi: () => void;
  private unsubscribeAgents?: () => void;
  private unsubscribeSimulation?: () => void;
  
  private lastSelectedZoneId: string | null = null;
  private lastCalamityType: string | null = null;

  constructor(
    zoneRenderer: ZoneRenderer,
    agentRenderer?: AgentRenderer,
    cameraController?: CameraController,
    disasterRenderer?: DisasterRenderer,
    infrastructureRenderer?: InfrastructureRenderer
  ) {
    this.zoneRenderer = zoneRenderer;
    this.agentRenderer = agentRenderer;
    this.cameraController = cameraController;
    this.disasterRenderer = disasterRenderer;
    this.infrastructureRenderer = infrastructureRenderer;

    // Listen to world state changes
    this.unsubscribeWorld = useStore.subscribe(
      (state: StoreState) => {
        this.zoneRenderer.updateZones(state.zones, state.safeZones);
        if (this.infrastructureRenderer) {
          // Future: update infrastructure from world state
          // this.infrastructureRenderer.updateInfrastructure(state.infrastructure);
        }
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
    
    // Listen to Simulation state changes for calamities
    if (this.disasterRenderer) {
      const state = useStore.getState();
      this.lastCalamityType = state.activeCalamity?.type || null;
      
      this.unsubscribeSimulation = useStore.subscribe(
        (state: StoreState) => {
          const currentCalamityType = state.activeCalamity?.type || null;
          
          // Only update if calamity identity changes (or if we need to stream continuous tick data later)
          if (currentCalamityType !== this.lastCalamityType) {
            this.lastCalamityType = currentCalamityType;
            this.disasterRenderer?.updateCalamity(state.activeCalamity);
          }
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
    if (this.disasterRenderer) {
      this.disasterRenderer.updateCalamity(state.activeCalamity);
    }
  }

  public dispose() {
    this.unsubscribeWorld();
    this.unsubscribeUi();
    if (this.unsubscribeAgents) {
      this.unsubscribeAgents();
    }
    if (this.unsubscribeSimulation) {
      this.unsubscribeSimulation();
    }
  }
}


