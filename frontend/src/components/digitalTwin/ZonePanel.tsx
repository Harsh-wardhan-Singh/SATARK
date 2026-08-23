import React from 'react';
import { useStore } from '../../store';
import './ZonePanel.css';

export const ZonePanel: React.FC = () => {
  const { selectedZoneId, zones, safeZones, setSelectedZoneId } = useStore();

  const selectedZone = zones.find(z => z.id === selectedZoneId);
  const isSafeZone = safeZones.some(sz => sz.zoneId === selectedZoneId);
  const safeZoneData = safeZones.find(sz => sz.zoneId === selectedZoneId);

  const handleFocusZone = () => {
    if (selectedZoneId) {
      window.dispatchEvent(
        new CustomEvent('satark:camera-focus-zone', {
          detail: { zoneId: selectedZoneId, force: true },
        })
      );
    }
  };

  const handleResetOverview = () => {
    window.dispatchEvent(new CustomEvent('satark:camera-reset-overview'));
  };

  if (!selectedZoneId) {
    return (
      <div className="zone-panel empty-state">
        <h3>Zone Information</h3>
        <p>No zone selected. Click on a zone overlay in the digital twin to view its information.</p>
        <button
          className="zone-panel-btn zone-panel-btn-secondary"
          onClick={handleResetOverview}
        >
          Reset Overview
        </button>
      </div>
    );
  }

  if (!selectedZone) {
    return (
      <div className="zone-panel error-state">
        <h3>Error</h3>
        <p>Selected zone not found in world state.</p>
        <button
          className="zone-panel-btn zone-panel-btn-secondary"
          onClick={() => setSelectedZoneId(null)}
        >
          Clear Selection
        </button>
      </div>
    );
  }

  return (
    <div className="zone-panel">
      <h3>Zone Information</h3>
      <div className="zone-details">
        {selectedZone.name && <p><strong>Name:</strong> {selectedZone.name}</p>}
        <p><strong>ID:</strong> {selectedZone.id}</p>
        <p><strong>Neighbors:</strong> {selectedZone.neighbors?.length || 0}</p>
        <p>
          <strong>Status:</strong>{' '}
          {isSafeZone ? (
            <span style={{ color: '#00ffaa' }}>Safe Zone (Capacity: {safeZoneData?.capacity})</span>
          ) : (
            <span style={{ color: '#00aaff' }}>Normal Zone</span>
          )}
        </p>
      </div>
      <div className="zone-panel-actions">
        <button
          className="zone-panel-btn zone-panel-btn-primary"
          onClick={handleFocusZone}
        >
          Focus Camera
        </button>
        <button
          className="zone-panel-btn zone-panel-btn-secondary"
          onClick={() => setSelectedZoneId(null)}
        >
          Deselect Zone
        </button>
      </div>
    </div>
  );
};

