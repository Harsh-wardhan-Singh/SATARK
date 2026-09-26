import React from 'react';

interface InterventionListProps {
  recommendations: any[];
  selectedInterventionIds: string[];
  onToggleIntervention: (id: string) => void;
}

export const InterventionList: React.FC<InterventionListProps> = ({
  recommendations,
  selectedInterventionIds,
  onToggleIntervention,
}) => {
  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="intervention-list">
        <p style={{ color: 'rgba(255,255,255,0.5)', fontStyle: 'italic', padding: '10px 0' }}>
          No recommendation returned
        </p>
      </div>
    );
  }

  return (
    <div className="intervention-list">
      {recommendations.map((rec: any) => {
        const id = rec.intervention?.intervention_id;
        if (!id) return null;
        return (
          <div className="intervention-item" key={id}>
            <input
              type="checkbox"
              checked={selectedInterventionIds.includes(id)}
              onChange={() => onToggleIntervention(id)}
            />
            <label>{rec.intervention?.name || id.replace(/_/g, ' ').toUpperCase()}</label>
          </div>
        );
      })}
    </div>
  );
};
