import React from 'react';

interface FinalSummarySectionProps {
  displayEnv: any;
  onClose: () => void;
}

export const FinalSummarySection: React.FC<FinalSummarySectionProps> = ({ displayEnv, onClose }) => {
  const casualties = displayEnv?.subsystems?.casualties;
  const infraDamage = displayEnv?.risk?.assessment?.breakdown?.infrastructure;

  return (
    <>
      <div className="final-summary">
        <h3>FINAL DISASTER SUMMARY</h3>
        <div className="summary-stats">
          <div className="stat-row">
            <span className="stat-label">FINAL RISK</span>
            <span className="stat-value">
              {displayEnv?.risk?.assessment?.composite_risk_score ?? 'NO DATA'}
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">AFFECTED</span>
            <span className="stat-value">
              {casualties
                ? (
                    (casualties.total_fatalities ?? 0) +
                    (casualties.total_injuries ?? 0)
                  ).toLocaleString()
                : 'NO DATA'}
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">INFRASTRUCTURE DAMAGE</span>
            <span className="stat-value">
              {infraDamage !== undefined ? `${infraDamage}%` : 'NO DATA'}
            </span>
          </div>
        </div>
      </div>

      <button className="close-disaster-btn" onClick={onClose}>
        CLOSE DISASTER
      </button>
    </>
  );
};
