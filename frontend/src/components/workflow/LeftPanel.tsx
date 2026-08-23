import React from 'react';
import { useStore } from '../../store';
import { ZonePanel } from '../digitalTwin/ZonePanel';
import { ZoneConfiguration } from './ZoneConfiguration';
import './LeftPanel.css';

export const LeftPanel: React.FC = () => {
  const { workflowState, selectedZoneId } = useStore();

  // Left Panel is only visible if a zone is selected OR a disaster is active/finished
  if (workflowState === 'idle') {
    return null;
  }

  return (
    <div className="left-panel">
      <div className="panel-content">
        {workflowState === 'zone-selected' && (
          <>
            {selectedZoneId ? (
              <ZonePanel />
            ) : (
              <div className="panel-placeholder">
                <p>No zone selected.</p>
              </div>
            )}
            <ZoneConfiguration />
          </>
        )}

        {workflowState === 'disaster-active' && (
          <div className="disaster-monitoring">
            <h3>DISASTER MONITORING</h3>
            <div className="monitoring-stats">
              <div className="stat-row">
                <span className="stat-label">STATUS</span>
                <span className="stat-value">ACTIVE</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">TIME REMAINING</span>
                <span className="stat-value">NO DATA</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">CASUALTIES</span>
                <span className="stat-value">NO DATA</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">PROPERTY DAMAGE</span>
                <span className="stat-value">NO DATA</span>
              </div>
            </div>
            <p className="backend-pending">Waiting for authoritative backend simulation data...</p>
          </div>
        )}

        {workflowState === 'disaster-finished' && (
          <div className="intervention-impact">
            <h3>INTERVENTION IMPACT</h3>
            <div className="impact-section">
              <h4>APPLIED MEASURES</h4>
              <p className="no-data">NO DATA</p>
            </div>
            <div className="impact-section">
              <h4>REDUCED EXPOSURE</h4>
              <p className="no-data">NO DATA</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
