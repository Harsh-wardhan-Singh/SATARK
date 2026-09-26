import React from 'react';
import { useStore } from '../../store';
import { RiskAssessmentSection } from '../impact/RiskAssessmentSection';
import { FinalSummarySection } from '../impact/FinalSummarySection';
import { RecommendationsSection } from '../recommendations/RecommendationsSection';
import './RightPanel.css';

export const RightPanel: React.FC = () => {
  const {
    workflowState,
    setWorkflowState,
    setSelectedZoneId,
    environment,
    finalEnvironment,
    setFinalEnvironment,
  } = useStore();

  // Right Panel is only visible if a disaster is active or finished
  if (workflowState !== 'disaster-active' && workflowState !== 'disaster-finished') {
    return null;
  }

  const handleCloseDisaster = () => {
    // Reset to idle state
    setWorkflowState('idle');
    setSelectedZoneId(null);
    setFinalEnvironment(undefined);
  };

  const displayEnv = workflowState === 'disaster-finished' ? finalEnvironment : environment;

  return (
    <div className="right-panel">
      <div className="panel-content">
        {workflowState === 'disaster-active' && (
          <>
            <RiskAssessmentSection environment={environment} />
            <RecommendationsSection />
          </>
        )}

        {workflowState === 'disaster-finished' && (
          <FinalSummarySection
            displayEnv={displayEnv}
            onClose={handleCloseDisaster}
          />
        )}
      </div>
    </div>
  );
};

