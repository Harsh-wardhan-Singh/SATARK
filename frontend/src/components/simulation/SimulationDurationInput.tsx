import React from 'react';

interface SimulationDurationInputProps {
  duration: number;
  maxDuration: number;
  durationUnit: string;
  onChangeDuration: (duration: number) => void;
}

export const SimulationDurationInput: React.FC<SimulationDurationInputProps> = ({
  duration,
  maxDuration,
  durationUnit,
  onChangeDuration,
}) => {
  return (
    <div className="form-group">
      <label>DURATION ({durationUnit})</label>
      <div className="duration-input-wrapper">
        <input
          type="number"
          min={1}
          max={maxDuration}
          value={duration}
          onChange={(e) =>
            onChangeDuration(
              Math.min(Math.max(1, parseInt(e.target.value) || 1), maxDuration)
            )
          }
          className="duration-input"
        />
        <span className="unit-label">{durationUnit}</span>
      </div>
      <div className="helper-text">
        Maximum: {maxDuration} {durationUnit.toLowerCase()}
      </div>
    </div>
  );
};
