import React from 'react';
import { useStore } from '../../store';
import './RightPanel.css';

export const RightPanel: React.FC = () => {
  const { workflowState, setWorkflowState, setSelectedZoneId } = useStore();

  // Right Panel is only visible if a disaster is active or finished
  if (workflowState !== 'disaster-active' && workflowState !== 'disaster-finished') {
    return null;
  }

  const handleCloseDisaster = () => {
    // Reset to idle state
    setWorkflowState('idle');
    setSelectedZoneId(null);
  };

  return (
    <div className="right-panel">
      <div className="panel-content">
        {workflowState === 'disaster-active' && (
          <>
            <div className="risk-section">
              <h3>RISK FACTOR</h3>
              <div className="risk-value">NO DATA</div>
              <p className="backend-pending">Waiting for authoritative risk data...</p>
            </div>

            <div className="interventions-section">
              <h3>RECOMMENDED INTERVENTIONS</h3>
              <div className="intervention-list">
                <div className="intervention-item disabled">
                  <input type="checkbox" disabled />
                  <label>Evacuation</label>
                </div>
                <div className="intervention-item disabled">
                  <input type="checkbox" disabled />
                  <label>Emergency shelters</label>
                </div>
                <div className="intervention-item disabled">
                  <input type="checkbox" disabled />
                  <label>Road closure</label>
                </div>
              </div>
              <button className="apply-btn" disabled>APPLY INTERVENTIONS</button>
            </div>
          </>
        )}

        {workflowState === 'disaster-finished' && (
          <>
            <div className="final-summary">
              <h3>FINAL DISASTER SUMMARY</h3>
              <div className="summary-stats">
                <div className="stat-row">
                  <span className="stat-label">FINAL RISK</span>
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
                <div className="stat-row">
                  <span className="stat-label">INFRASTRUCTURE DAMAGE</span>
                  <span className="stat-value">NO DATA</span>
                </div>
              </div>
            </div>
            
            <button className="close-disaster-btn" onClick={handleCloseDisaster}>
              CLOSE DISASTER
            </button>
          </>
        )}
      </div>
    </div>
  );
};
