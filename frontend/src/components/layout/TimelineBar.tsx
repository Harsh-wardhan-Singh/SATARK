import React from 'react';
import { useStore } from '../../store';
import './TimelineBar.css';

export const TimelineBar: React.FC = () => {
  const { status, currentTick } = useStore();
  const isRunning = status === 'running';

  return (
    <div className="timeline-bar">
      <div className="timeline-status">
        {isRunning ? (
          <span className="timeline-active">TICK: {currentTick}</span>
        ) : (
          <span className="timeline-empty">NO SIMULATION DATA</span>
        )}
      </div>
      <div className="timeline-track">
        {/* Visual placeholder for future timeline slider */}
        <div className="timeline-progress" style={{ width: isRunning ? '50%' : '0%' }}></div>
      </div>
      <div className="timeline-controls disabled">
        <button disabled>|&lt;</button>
        <button disabled>&lt;</button>
        <button disabled>&gt;</button>
        <button disabled>&gt;|</button>
      </div>
    </div>
  );
};
