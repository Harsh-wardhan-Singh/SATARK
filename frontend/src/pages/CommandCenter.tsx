import React from 'react';
import { CommandCenterLayout } from '../components/layout/CommandCenterLayout';
import { CityScene } from '../components/twin/CityScene';
import { GisMapView } from '../components/gis/GisMapView';
import { ForecastSlider } from '../components/simulation/ForecastSlider';
import { CommandHeader } from '../components/layout/CommandHeader';
import { TimelineBar } from '../components/layout/TimelineBar';
import { LeftPanel } from '../components/workflow/LeftPanel';
import { RightPanel } from '../components/workflow/RightPanel';
import { CompactControls } from '../components/workflow/CompactControls';
import { SimulationLoopManager } from '../components/workflow/SimulationLoopManager';
import { useStore } from '../store';

export const CommandCenter: React.FC = () => {
  const { viewportMode, workflowState } = useStore();

  return (
    <>
      <SimulationLoopManager />
      <CommandCenterLayout
        header={<CommandHeader />}
        leftSidebar={<LeftPanel />}
        rightSidebar={<RightPanel />}
        main={
          <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
            {viewportMode === '3d' ? <CityScene /> : <GisMapView />}
            <CompactControls />
            {workflowState === 'disaster-active' && (
              <div
                style={{
                  position: 'absolute',
                  top: '16px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  zIndex: 500,
                }}
              >
                <ForecastSlider />
              </div>
            )}
          </div>
        }
        footer={<TimelineBar />}
      />
    </>
  );
};

