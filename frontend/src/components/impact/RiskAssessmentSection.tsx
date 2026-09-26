import React from 'react';

interface RiskAssessmentSectionProps {
  environment: any;
}

export const RiskAssessmentSection: React.FC<RiskAssessmentSectionProps> = ({ environment }) => {
  const risk = environment?.risk;
  const casualties = environment?.subsystems?.casualties;
  const isAvailable = Boolean(risk?.available && risk.assessment);
  const assessment = risk?.assessment;

  return (
    <div className="risk-section" style={{ marginBottom: '20px' }}>
      <h3>RISK ASSESSMENT</h3>
      {isAvailable && assessment ? (
        <>
          <div className="stat-row">
            <span className="stat-label">Risk Score</span>
            <span className="stat-value">{assessment.composite_risk_score}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Severity</span>
            <span className="stat-value">{assessment.severity_label}</span>
          </div>
          <div className="stat-row" style={{ marginTop: '10px' }}>
            <span className="stat-label">Infrastructure Risk</span>
            <span className="stat-value">
              {assessment.breakdown?.infrastructure !== undefined
                ? `${assessment.breakdown.infrastructure}%`
                : 'N/A'}
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Estimated Affected</span>
            <span className="stat-value">
              {casualties
                ? (
                    (casualties.total_fatalities ?? 0) +
                    (casualties.total_injuries ?? 0)
                  ).toLocaleString()
                : 'Unavailable'}
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Flooding Risk</span>
            <span className="stat-value">
              {assessment.breakdown?.flooding !== undefined
                ? `${assessment.breakdown.flooding}%`
                : 'N/A'}
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Congestion Risk</span>
            <span className="stat-value">
              {assessment.breakdown?.congestion !== undefined
                ? `${assessment.breakdown.congestion}%`
                : 'N/A'}
            </span>
          </div>
        </>
      ) : (
        <div className="intervention-list">
          <p style={{ color: 'rgba(255,255,255,0.5)', fontStyle: 'italic', padding: '10px 0' }}>
            Risk unavailable
          </p>
        </div>
      )}
    </div>
  );
};
