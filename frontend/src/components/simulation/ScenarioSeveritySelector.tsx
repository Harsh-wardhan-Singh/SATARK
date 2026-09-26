import React from 'react';

interface ScenarioSeveritySelectorProps {
  severity: string;
  onSelectSeverity: (severity: string) => void;
}

export const ScenarioSeveritySelector: React.FC<ScenarioSeveritySelectorProps> = ({
  severity,
  onSelectSeverity,
}) => {
  return (
    <div className="form-group">
      <label>SEVERITY</label>
      <div className="button-group">
        <button
          className={`config-btn ${severity === 'Low' ? 'active' : ''}`}
          onClick={() => onSelectSeverity('Low')}
        >
          LOW
        </button>
        <button
          className={`config-btn ${severity === 'Medium' ? 'active' : ''}`}
          onClick={() => onSelectSeverity('Medium')}
        >
          MEDIUM
        </button>
        <button
          className={`config-btn ${severity === 'High' ? 'active' : ''}`}
          onClick={() => onSelectSeverity('High')}
        >
          HIGH
        </button>
      </div>
    </div>
  );
};
