import React from 'react';
import { ViewportModeToggle } from './ViewportModeToggle';
import { useStore } from '../../store';
import './CommandHeader.css';

export const CommandHeader: React.FC = () => {
  const { workflowState, activeCalamity } = useStore();

  const getStatusText = () => {
    switch (workflowState) {
      case 'disaster-active':
        return 'ACTIVE SIMULATION';
      case 'disaster-finished':
        return 'SIMULATION FINISHED';
      case 'zone-selected':
        return 'ZONE SELECTED';
      default:
        return 'STANDBY';
    }
  };

  const getStatusClass = () => {
    switch (workflowState) {
      case 'disaster-active':
        return 'status-running';
      case 'disaster-finished':
        return 'status-completed';
      case 'zone-selected':
        return 'status-paused';
      default:
        return 'status-idle';
    }
  };

  return (
    <div className="command-header">
      <div className="command-header-brand">
        <h1>SATARK</h1>
        <span className="brand-subtitle">DISASTER-RESPONSE DIGITAL TWIN</span>
      </div>

      <ViewportModeToggle />

      <div className="command-header-metrics">
        <div className="metric">
          <span className="metric-label">CALAMITY</span>
          <span className="metric-value">
            {activeCalamity?.type ?? 'FLOOD'}
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">SYSTEM STATUS</span>
          <span className={`metric-value ${getStatusClass()}`}>
            {getStatusText()}
          </span>
        </div>
      </div>
    </div>
  );
};

