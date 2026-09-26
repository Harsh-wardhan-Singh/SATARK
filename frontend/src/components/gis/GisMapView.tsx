import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useStore } from '../../store';
import { fetchZones, fetchSafeZones } from '../../api/worldApi';
import { fetchNowcast, NowcastResponse } from '../../api/simulationApi';
import { Zone, SafeZone } from '../../types/domain';
import './GisMapView.css';

// Project normalized zone coordinates into Mumbai metro coastal coordinates
function zoneToLatLng(normalizedX: number, normalizedY: number): [number, number] {
  const lat = 19.00 + normalizedY * 0.16;
  const lng = 72.82 + normalizedX * 0.11;
  return [lat, lng];
}

function getDepthColor(depthCm: number): string {
  if (depthCm >= 30) return '#ef4444'; // Critical
  if (depthCm >= 15) return '#f59e0b'; // Hazard
  if (depthCm >= 5) return '#06b6d4';  // Minor
  return '#10b981';                    // Safe / Nominal
}

export const GisMapView: React.FC = () => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);

  const {
    selectedZoneId,
    setSelectedZoneId,
    environment,
    workflowState,
    forecastHorizonHours,
    currentTick,
  } = useStore();

  const [zones, setZones] = useState<Zone[]>([]);
  const [safeZones, setSafeZones] = useState<SafeZone[]>([]);
  const [nowcast, setNowcast] = useState<NowcastResponse | null>(null);

  // 1. Fetch zone definitions and safe zones on mount
  useEffect(() => {
    let isMounted = true;
    const loadWorld = async () => {
      try {
        const [zList, sList] = await Promise.all([fetchZones(), fetchSafeZones()]);
        if (isMounted) {
          setZones(zList);
          setSafeZones(sList);
        }
      } catch (err) {
        console.error('Failed to load GIS zones:', err);
      }
    };
    loadWorld();
    return () => {
      isMounted = false;
    };
  }, []);

  // 2. Fetch nowcast projections when disaster is active
  useEffect(() => {
    if (workflowState !== 'disaster-active') {
      setNowcast(null);
      return;
    }
    let isMounted = true;
    const loadNowcast = async () => {
      try {
        const res = await fetchNowcast([1.0, 2.0, 3.0]);
        if (isMounted) setNowcast(res);
      } catch (err) {
        console.warn('Nowcast data not yet ready:', err);
      }
    };
    loadNowcast();
    return () => {
      isMounted = false;
    };
  }, [workflowState, currentTick]);

  // 3. Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Centered on Mumbai coastal metro
    const map = L.map(mapContainerRef.current, {
      center: [19.076, 72.877],
      zoom: 12,
      zoomControl: false,
      attributionControl: true,
    });

    // Dark Matter tile layer
    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      {
        maxZoom: 19,
        subdomains: 'abcd',
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      }
    ).addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;
    layerGroupRef.current = layerGroup;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      layerGroupRef.current = null;
    };
  }, []);

  // 4. Render and update Zone Overlays & Flood Contours
  useEffect(() => {
    const layerGroup = layerGroupRef.current;
    if (!layerGroup || zones.length === 0) return;

    layerGroup.clearLayers();

    const safeZoneIds = new Set(safeZones.map((s) => s.zoneId));
    const liveDepths = environment?.flood_water_levels || {};
    const drainageState = environment?.drainage?.zone_drainage || {};

    // Get depth for active horizon
    let projectedDepths: Record<string, number> = {};
    if (forecastHorizonHours > 0 && nowcast?.horizons) {
      const proj = nowcast.horizons.find(
        (h) => Math.round(h.horizon_hours) === forecastHorizonHours
      );
      if (proj) {
        projectedDepths = proj.water_depth_cm;
      }
    }

    zones.forEach((zone) => {
      const normX = zone.center_normalized?.x ?? 0.5;
      const normY = zone.center_normalized?.y ?? 0.5;
      const [lat, lng] = zoneToLatLng(normX, normY);

      // Determine depth in cm
      let depthCm = 0;
      if (forecastHorizonHours === 0) {
        depthCm = Math.round((liveDepths[zone.id] ?? 0) * 100);
      } else {
        depthCm = Math.round(projectedDepths[zone.id] ?? 0);
      }

      const isSafe = safeZoneIds.has(zone.id);
      const isSelected = selectedZoneId === zone.id;
      const color = isSafe ? '#10b981' : getDepthColor(depthCm);

      const zd = drainageState[zone.id];
      const isSurcharging = Boolean(zd?.is_surcharging || (zd?.pipe_utilization ?? 0) > 1.0);

      // Create interactive circle contour
      const circle = L.circle([lat, lng], {
        radius: 1100,
        color: isSelected ? '#38bdf8' : isSurcharging ? '#f97316' : color,
        weight: isSelected ? 3.5 : isSurcharging ? 2.5 : 1.5,
        dashArray: isSurcharging ? '6, 6' : undefined,
        fillColor: color,
        fillOpacity: isSelected ? 0.65 : 0.45,
      });

      // Tooltip with ward short name
      const shortWard = zone.ward_name ? ` (${zone.ward_name.split('/')[0].trim()})` : '';
      circle.bindTooltip(`${zone.id}${shortWard}: ${depthCm} cm`, {
        permanent: true,
        direction: 'center',
        className: 'gis-zone-tooltip',
      });

      // Click Selection
      circle.on('click', () => {
        setSelectedZoneId(zone.id);
      });

      // Detailed Info Popup
      const popupHtml = `
        <div class="gis-popup-content">
          <div class="gis-popup-header">
            <span>${zone.id} - ${zone.ward_name || 'Urban Zone'}</span>
            ${isSafe ? '<span style="color:#10b981;font-size:10px;">[SAFE ZONE]</span>' : ''}
          </div>
          ${zone.ward_code ? `<div style="font-size:10px;color:#38bdf8;margin-bottom:4px;">${zone.ward_code} • ${zone.primary_land_use || ''}</div>` : ''}
          <div class="gis-popup-stat">
            <span>Water Depth:</span>
            <span style="color:${getDepthColor(depthCm)};">${depthCm} cm</span>
          </div>
          <div class="gis-popup-stat">
            <span>Elevation:</span>
            <span>${(zone.elevation ?? zone.center_normalized?.y ?? 0.5).toFixed(2)}m</span>
          </div>
          <div class="gis-popup-stat">
            <span>Classification:</span>
            <span style="color:#cbd5e1;">${zone.risk_classification || 'Standard Ward'}</span>
          </div>
          <div class="gis-popup-stat">
            <span>Drainage Status:</span>
            <span style="color:${isSurcharging ? '#f97316' : '#94a3b8'};">
              ${isSurcharging ? 'PIPE SURCHARGE' : 'NORMAL'}
            </span>
          </div>
          <div class="gis-popup-stat">
            <span>Status:</span>
            <span>${depthCm > 30 ? 'CRITICAL / FLOODED' : depthCm > 5 ? 'PONDING' : 'DRY'}</span>
          </div>
        </div>
      `;
      circle.bindPopup(popupHtml);

      layerGroup.addLayer(circle);
    });
  }, [
    zones,
    safeZones,
    selectedZoneId,
    environment,
    forecastHorizonHours,
    nowcast,
    setSelectedZoneId,
  ]);

  return (
    <div className="gis-map-wrapper">
      <div id="satark-gis-map" ref={mapContainerRef} className="gis-map-container" />

      {/* 2D GIS Map Legend */}
      <div className="gis-map-legend">
        <div className="legend-title">Flood Contours</div>
        <div className="legend-items">
          <div className="legend-item">
            <div className="legend-color-box" style={{ background: '#10b981' }} />
            <span>&lt; 5 cm (Safe / Nominal)</span>
          </div>
          <div className="legend-item">
            <div className="legend-color-box" style={{ background: '#06b6d4' }} />
            <span>5 – 15 cm (Minor Ponding)</span>
          </div>
          <div className="legend-item">
            <div className="legend-color-box" style={{ background: '#f59e0b' }} />
            <span>15 – 30 cm (Hazardous)</span>
          </div>
          <div className="legend-item">
            <div className="legend-color-box" style={{ background: '#ef4444' }} />
            <span>&gt; 30 cm (Critical Impassable)</span>
          </div>
          <div className="legend-item" style={{ marginTop: '4px', borderTop: '1px solid #334155', paddingTop: '4px' }}>
            <span style={{ color: '#10b981', fontWeight: 'bold' }}>●</span>
            <span>Safe Zones (Backend Predefined)</span>
          </div>
          <div className="legend-item">
            <span style={{ color: '#f97316', fontWeight: 'bold' }}>◌</span>
            <span>Pipe Surcharge Warning</span>
          </div>
        </div>
      </div>
    </div>
  );
};
