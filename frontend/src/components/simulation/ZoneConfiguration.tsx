import React, { useEffect, useState } from 'react';
import { useStore } from '../../store';
import {
  initializeSimulation,
  fetchSimulationPresets,
  DisasterScenarioPreset,
} from '../../api/simulationApi';
import { ScenarioSeveritySelector } from './ScenarioSeveritySelector';
import { SimulationDurationInput } from './SimulationDurationInput';
import '../workflow/ZoneConfiguration.css';

export const ZoneConfiguration: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [duration, setDuration] = useState<number>(3); // Default 3 days for Flood
  const [severity, setSeverity] = useState<string>('Medium');
  const [activePresetId, setActivePresetId] = useState<string | null>(null);
  const [presets, setPresets] = useState<DisasterScenarioPreset[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { selectedZoneId, setSelectedZoneId, applyWorldSnapshot, setWorkflowState } = useStore();

  const maxDuration = 7;
  const durationUnit = 'DAYS';

  useEffect(() => {
    let isMounted = true;
    const loadPresets = async () => {
      try {
        const list = await fetchSimulationPresets();
        if (isMounted) setPresets(list);
      } catch (err) {
        console.warn('Failed to load presets:', err);
      }
    };
    loadPresets();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleApplyPreset = (preset: DisasterScenarioPreset) => {
    setActivePresetId(preset.id);
    setDuration(preset.duration_days);
    setSeverity(preset.severity_label === 'Extreme' ? 'High' : preset.severity_label);
    if (!selectedZoneId || selectedZoneId !== preset.target_zone) {
      setSelectedZoneId(preset.target_zone);
    }
  };

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

      const activePreset = presets.find((p) => p.id === activePresetId);
      const rainfallIntensity = activePreset
        ? activePreset.rainfall_intensity
        : (severityMap[severity] || 2) * 20.0;

      const hyetographType = activePreset
        ? activePreset.hyetograph_type
        : 'CONSTANT';

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
          rainfall_intensity: rainfallIntensity,
          hyetograph_type: hyetographType,
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

  const selectedPreset = presets.find((p) => p.id === activePresetId);

  return (
    <div className="zone-configuration">
      <div className="config-header">
        <h4>DISASTER CONFIGURATION</h4>
        <button className="collapse-btn" onClick={() => setIsExpanded(false)}>
          &times;
        </button>
      </div>

      <div className="config-body">
        {presets.length > 0 && (
          <div className="form-group">
            <label>BENCHMARK SCENARIO PRESETS</label>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
                marginBottom: '8px',
              }}
            >
              {presets.map((p) => (
                <button
                  key={p.id}
                  className={`config-btn ${activePresetId === p.id ? 'active' : ''}`}
                  onClick={() => handleApplyPreset(p)}
                  style={{
                    textAlign: 'left',
                    padding: '8px 10px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    gap: '2px',
                  }}
                >
                  <span style={{ fontWeight: 700 }}>{p.name}</span>
                  <span style={{ fontSize: '10px', opacity: 0.8 }}>
                    {p.rainfall_intensity} mm/h • {p.target_ward}
                  </span>
                </button>
              ))}
            </div>
            {selectedPreset && (
              <p
                style={{
                  fontSize: '10px',
                  color: '#94a3b8',
                  fontStyle: 'italic',
                  lineHeight: '1.4',
                  margin: '4px 0 8px 0',
                }}
              >
                {selectedPreset.description}
              </p>
            )}
          </div>
        )}

        <div className="form-group">
          <label>SCENARIO / CALAMITY</label>
          <div className="button-group">
            <button className="config-btn active">URBAN FLOOD NOWCAST</button>
          </div>
        </div>

        <ScenarioSeveritySelector
          severity={severity}
          onSelectSeverity={(sev) => {
            setActivePresetId(null);
            setSeverity(sev);
          }}
        />

        <SimulationDurationInput
          duration={duration}
          maxDuration={maxDuration}
          durationUnit={durationUnit}
          onChangeDuration={(dur) => {
            setActivePresetId(null);
            setDuration(dur);
          }}
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

