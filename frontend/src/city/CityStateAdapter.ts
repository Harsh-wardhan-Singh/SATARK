import { useStore, StoreState } from '../store';
import { ZoneRenderer } from './zones/ZoneRenderer';
import { AgentRenderer } from './agents/AgentRenderer';

export class CityStateAdapter {
  private zoneRenderer: ZoneRenderer;
  private agentRenderer?: AgentRenderer;
  private unsubscribeWorld: () => void;
  private unsubscribeUi: () => void;
  private unsubscribeAgents?: () => void;

  constructor(zoneRenderer: ZoneRenderer, agentRenderer?: AgentRenderer) {
    this.zoneRenderer = zoneRenderer;
    this.agentRenderer = agentRenderer;

    // Listen to world state changes
    this.unsubscribeWorld = useStore.subscribe(
      (state: StoreState) => {
        this.zoneRenderer.updateZones(state.zones, state.safeZones);
      }
    );

    // Listen to UI state changes
    this.unsubscribeUi = useStore.subscribe(
      (state: StoreState) => {
        this.zoneRenderer.setSelectedZone(state.selectedZoneId);
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

