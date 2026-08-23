import React from 'react';
import { useStore } from '../../store';

export const SimulationControls: React.FC = () => {
  const { status, currentTick } = useStore();

  return (
    <div className="simulation-controls">
      <h3>Simulation Controls</h3>
      <p>Status: {status}</p>
      <p>Tick: {currentTick}</p>
      {/* Controls will be added here */}
    </div>
  );
};
