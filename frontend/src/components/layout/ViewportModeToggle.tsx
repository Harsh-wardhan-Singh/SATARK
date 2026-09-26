import React from 'react';
import { useStore } from '../../store';
import './ViewportModeToggle.css';

export const ViewportModeToggle: React.FC = () => {
  const { viewportMode, setViewportMode } = useStore();

  return (
    <div className="viewport-mode-toggle">
      <button
        className={`mode-toggle-btn ${viewportMode === '3d' ? 'active' : ''}`}
        onClick={() => setViewportMode('3d')}
        title="3D Holographic Digital Twin Command Center"
      >
        <span>3D VIEW</span>
      </button>

      <button
        className={`mode-toggle-btn ${viewportMode === '2d' ? 'active' : ''}`}
        onClick={() => setViewportMode('2d')}
        title="2D OpenStreetMap GIS Heatmap & Contours"
      >
        <span>2D VIEW</span>
      </button>
    </div>
  );
};
