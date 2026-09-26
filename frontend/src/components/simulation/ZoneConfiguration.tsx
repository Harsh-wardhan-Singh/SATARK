import React, { useState } from 'react';
import { useStore } from '../../store';
import { initializeSimulation } from '../../api/simulationApi';
import { ScenarioSeveritySelector } from './ScenarioSeveritySelector';
import { SimulationDurationInput } from './SimulationDurationInput';
import '../workflow/ZoneConfiguration.css';

export const ZoneConfiguration: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [duration, setDuration] = useState<number>(3); // Default 3 days for Flood
  const [severity, setSeverity] = useState<string>('Medium');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { selectedZoneId, applyWorldSnapshot, setWorkflowState } = useStore();

  const maxDuration = 7;
  const durationUnit = 'DAYS';

  const handleStartSimulation = async () => {
    if (!selectedZoneId) {
      setError('Please select a zone first.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const payloadDuration = duration * 86400;
      const severityMap: Record<string, number> = { Low: 1, Medium: 2, High: 3 };

      const payload = {
        duration: payloadDuration,
        tick_rate: 1.0 / 3600.0, // FLOOD: 1 tick = 1 hour
        calamity_type: 'FLOOD' as const,
        parameters: {
          zone_mapping_path: 'data/glb_zone_mapping.json',
          infrastructure_path: 'data/infrastructure.json',
          population_path: 'data/population.json',
          shelters_path: 'data/shelters.json',
          representative_agent_count: 250,
          severity: severityMap[severity] || 2,
          rainfall_intensity: (severityMap[severity] || 2) * 20.0,
          intervention_level: 0.0,
          zone_id: selectedZoneId,
        },
      };

      const snapshot = await initializeSimulation(payload);
      applyWorldSnapshot(snapshot);
      setWorkflowState('disaster-active');
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  };

  if (!isExpanded) {
    return (
      <div className="zone-configuration-collapsed">
        <button className="simulate-btn" onClick={() => setIsExpanded(true)}>
          SIMULATE DISASTER
        </button>
      </div>
    );
  }

  return (
    <div className="zone-configuration">
      <div className="config-header">
        <h4>DISASTER CONFIGURATION</h4>
        <button className="collapse-btn" onClick={() => setIsExpanded(false)}>
          &times;
        </button>
      </div>

      <div className="config-body">
        <div className="form-group">
          <label>SCENARIO / CALAMITY</label>
          <div className="button-group">
            <button className="config-btn active">URBAN FLOOD NOWCAST</button>
          </div>
        </div>

        <ScenarioSeveritySelector
          severity={severity}
          onSelectSeverity={setSeverity}
        />

        <SimulationDurationInput
          duration={duration}
          maxDuration={maxDuration}
          durationUnit={durationUnit}
          onChangeDuration={setDuration}
        />

        {error && (
          <div className="error-message" style={{ color: '#ff4d4f', marginBottom: '10px' }}>
            {error}
          </div>
        )}

        <button
          className="simulate-action-btn"
          onClick={handleStartSimulation}
          disabled={loading}
        >
          {loading ? 'INITIALIZING...' : 'START SIMULATION'}
        </button>
      </div>
    </div>
  );
};
