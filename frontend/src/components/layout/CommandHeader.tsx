import React, { useEffect, useState } from 'react';
import { useStore } from '../../store';
import './CommandHeader.css';

export const CommandHeader: React.FC = () => {
  const { status, activeCalamity } = useStore();
  const [cameraMode, setCameraMode] = useState<'ORTHOGRAPHIC' | 'FREECAM'>('ORTHOGRAPHIC');

  useEffect(() => {
    const handleCameraModeChange = (e: CustomEvent) => {
      if (e.detail?.mode) {
        setCameraMode(e.detail.mode.toUpperCase());
      }
    };
    window.addEventListener('satark:camera-mode-changed', handleCameraModeChange as EventListener);
    return () => {
      window.removeEventListener('satark:camera-mode-changed', handleCameraModeChange as EventListener);
    };
  }, []);

  return (
    <div className="command-header">
      <div className="command-header-brand">
        <h1>SATARK</h1>
        <span className="brand-subtitle">COMMAND CENTER</span>
      </div>
      <div className="command-header-metrics">
        <div className="metric">
          <span className="metric-label">SIMULATION</span>
          <span className={`metric-value status-${status}`}>{status.toUpperCase()}</span>
        </div>
        <div className="metric">
          <span className="metric-label">CALAMITY</span>
          <span className="metric-value">{activeCalamity ? activeCalamity.type.toUpperCase() : 'NONE'}</span>
        </div>
        <div className="metric">
          <span className="metric-label">BACKEND</span>
          <span className="metric-value status-disconnected">DISCONNECTED</span>
        </div>
        <div className="metric">
          <span className="metric-label">CAMERA</span>
          <span className="metric-value">{cameraMode}</span>
        </div>
      </div>
    </div>
  );
};
