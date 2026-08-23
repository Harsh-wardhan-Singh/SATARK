import React from 'react';
import { useStore } from '../../store';
import './ZonePanel.css';

export const ZonePanel: React.FC = () => {
  const { selectedZoneId, zones, safeZones, setSelectedZoneId } = useStore();

  const selectedZone = zones.find(z => z.id === selectedZoneId);
  const isSafeZone = safeZones.some(sz => sz.zoneId === selectedZoneId);
  const safeZoneData = safeZones.find(sz => sz.zoneId === selectedZoneId);

  if (!selectedZoneId) {
    return (
      <div className="zone-panel empty-state">
        <h3>Zone Information</h3>
        <p>No zone selected. Click on a zone overlay in the digital twin to view its information.</p>
      </div>
    );
  }

  if (!selectedZone) {
    return (
      <div className="zone-panel error-state">
        <h3>Error</h3>
        <p>Selected zone not found in world state.</p>
        <button onClick={() => setSelectedZoneId(null)}>Clear Selection</button>
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
      <button 
        onClick={() => setSelectedZoneId(null)} 
        style={{ marginTop: '1rem', padding: '0.5rem', background: '#333', color: 'white', border: '1px solid #555', borderRadius: '4px', cursor: 'pointer', width: '100%' }}
      >
        Deselect Zone
      </button>
    </div>
  );
};
