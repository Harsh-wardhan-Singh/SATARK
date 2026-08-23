import { useStore, StoreState } from '../store';
import { ZoneRenderer } from './zones/ZoneRenderer';

export class CityStateAdapter {
  private zoneRenderer: ZoneRenderer;
  private unsubscribeWorld: () => void;
  private unsubscribeUi: () => void;

  constructor(zoneRenderer: ZoneRenderer) {
    this.zoneRenderer = zoneRenderer;

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

    // Initial sync
    const state = useStore.getState();
    this.zoneRenderer.updateZones(state.zones, state.safeZones);
    this.zoneRenderer.setSelectedZone(state.selectedZoneId);
  }

  public dispose() {
    this.unsubscribeWorld();
    this.unsubscribeUi();
  }
}
