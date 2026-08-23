import React, { useState } from 'react';
import { CalamityType } from '../../types/domain';
import './ZoneConfiguration.css';

export const ZoneConfiguration: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [disasterType, setDisasterType] = useState<CalamityType>('Flood');
  const [duration, setDuration] = useState<number>(3); // Default 3 days for Flood
  const [severity, setSeverity] = useState<string>('Medium');

  const handleTypeChange = (type: CalamityType) => {
    setDisasterType(type);
    if (type === 'Flood') {
      setDuration(3);
    } else {
      setDuration(15); // Default 15 mins for Earthquake
    }
  };

  const maxDuration = disasterType === 'Flood' ? 7 : 60;
  const durationUnit = disasterType === 'Flood' ? 'DAYS' : 'MINUTES';

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
        <button className="collapse-btn" onClick={() => setIsExpanded(false)}>&times;</button>
      </div>
      
      <div className="config-body">
        <div className="form-group">
          <label>CALAMITY TYPE</label>
          <div className="button-group">
            <button 
              className={`config-btn ${disasterType === 'Flood' ? 'active' : ''}`}
              onClick={() => handleTypeChange('Flood')}
            >
              FLOOD
            </button>
            <button 
              className={`config-btn ${disasterType === 'Earthquake' ? 'active' : ''}`}
              onClick={() => handleTypeChange('Earthquake')}
            >
              EARTHQUAKE
            </button>
          </div>
        </div>

        <div className="form-group">
          <label>SEVERITY</label>
          <div className="button-group">
            <button 
              className={`config-btn ${severity === 'Low' ? 'active' : ''}`}
              onClick={() => setSeverity('Low')}
            >
              LOW
            </button>
            <button 
              className={`config-btn ${severity === 'Medium' ? 'active' : ''}`}
              onClick={() => setSeverity('Medium')}
            >
              MEDIUM
            </button>
            <button 
              className={`config-btn ${severity === 'High' ? 'active' : ''}`}
              onClick={() => setSeverity('High')}
            >
              HIGH
            </button>
          </div>
        </div>

        <div className="form-group">
          <label>DURATION ({durationUnit})</label>
          <div className="duration-input-wrapper">
            <input 
              type="number" 
              min={1} 
              max={maxDuration} 
              value={duration}
              onChange={(e) => setDuration(Math.min(Math.max(1, parseInt(e.target.value) || 1), maxDuration))}
              className="duration-input"
            />
            <span className="unit-label">{durationUnit}</span>
          </div>
          <div className="helper-text">Maximum: {maxDuration} {durationUnit.toLowerCase()}</div>
        </div>

        {/* Backend integration pending */}
        <button className="simulate-action-btn" disabled title="Backend integration pending">
          START SIMULATION (PENDING BACKEND)
        </button>
      </div>
    </div>
  );
};
