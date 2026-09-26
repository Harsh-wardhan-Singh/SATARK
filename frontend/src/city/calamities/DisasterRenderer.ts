import { Calamity, FloodEnvironment } from '../../types/domain';
import { FloodRenderer } from './flood/FloodRenderer';
import { ZoneRenderer } from '../zones/ZoneRenderer';

import { CityRenderer } from '../CityRenderer';

export class DisasterRenderer {
  private floodRenderer: FloodRenderer;

  constructor(renderer: CityRenderer, zoneRenderer: ZoneRenderer) {
    this.floodRenderer = new FloodRenderer(renderer, zoneRenderer);
  }

  public updateCalamity(calamity: Calamity | null, environment?: FloodEnvironment) {
    if (!calamity) {
      this.floodRenderer.clear();
      return;
    }

    if (calamity.type === 'FLOOD') {
      this.floodRenderer.render(calamity, environment);
    }
  }

  public clear() {
    this.updateCalamity(null);
  }

  public dispose() {
    this.floodRenderer.dispose();
  }
}

