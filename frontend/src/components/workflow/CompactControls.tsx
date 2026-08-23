import React, { useEffect, useState } from 'react';
import './CompactControls.css';

export const CompactControls: React.FC = () => {
  const [cameraMode, setCameraMode] = useState<'orthographic' | 'freecam'>('orthographic');

  useEffect(() => {
    const handleCameraModeChange = (e: CustomEvent) => {
      if (e.detail?.mode) {
        setCameraMode(e.detail.mode);
      }
    };
    window.addEventListener('satark:camera-mode-changed', handleCameraModeChange as EventListener);
    return () => {
      window.removeEventListener('satark:camera-mode-changed', handleCameraModeChange as EventListener);
    };
  }, []);

  const handleResetOverview = () => {
    window.dispatchEvent(new CustomEvent('satark:camera-reset-overview'));
  };

  const handleFreecam = () => {
    window.dispatchEvent(
      new CustomEvent('satark:camera-change-mode', {
        detail: { mode: 'freecam' },
      })
    );
  };

  const handleOrthographic = () => {
    window.dispatchEvent(
      new CustomEvent('satark:camera-change-mode', {
        detail: { mode: 'orthographic' },
      })
    );
  };

  return (
    <div className="compact-controls">
      <div className="compact-controls-header">CAMERA</div>
      <div className="compact-button-group">
        <button 
          className={`compact-btn ${cameraMode === 'orthographic' ? 'active' : ''}`} 
          onClick={handleOrthographic}
          title="Strategic Camera"
        >
          STRAT
        </button>
        <button 
          className={`compact-btn ${cameraMode === 'freecam' ? 'active' : ''}`} 
          onClick={handleFreecam}
          title="Freecam"
        >
          FREE
        </button>
        <button 
          className="compact-btn" 
          onClick={handleResetOverview}
          title="Reset Overview"
        >
          RST
        </button>
      </div>
    </div>
  );
};
