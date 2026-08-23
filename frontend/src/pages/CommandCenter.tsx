import React from 'react';
import { CommandCenterLayout } from '../components/layout/CommandCenterLayout';
import { CityScene } from '../components/twin/CityScene';
import { SimulationControls } from '../components/simulation/SimulationControls';
import { ZonePanel } from '../components/digitalTwin/ZonePanel';
import { StatusBar } from '../components/telemetry/StatusBar';

export const CommandCenter: React.FC = () => {
  return (
    <CommandCenterLayout
      header={<h2>SATARK Command Center</h2>}
      sidebar={
        <>
          <ZonePanel />
          <SimulationControls />
        </>
      }
      main={<CityScene />}
      footer={<StatusBar />}
    />
  );
};
