import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useStore } from '../../store';
import { fetchZones, fetchSafeZones } from '../../api/worldApi';
import { fetchNowcast, NowcastResponse } from '../../api/simulationApi';
import { Zone, SafeZone } from '../../types/domain';
import './GisMapView.css';

// Authoritative Real-World Geographic Coordinates for SATARK's 21 Simulation Wards
// Distributed across the South Mumbai peninsula (Menaka/Navy Nagar up to Ballard Estate) matching the 3D model footprint
export const MUMBAI_ZONE_GEO: Record<string, [number, number]> = {
  Z01: [18.9195, 72.8235], // Colaba Causeway Central
  Z02: [18.9215, 72.8160], // Cuffe Parade South / Badhwar Park
  Z03: [18.9230, 72.8260], // Strand Cinema / Colaba West
  Z04: [18.9280, 72.8315], // Regal Circle / SP Chowk
  Z05: [18.9375, 72.8285], // Churchgate / Oval Maidan
  Z06: [18.9360, 72.8230], // Marine Drive / Back Bay Shoreline
  Z07: [18.9410, 72.8330], // Fort North / Flora Fountain
  Z08: [18.9310, 72.8260], // Mantralaya / Back Bay East
  Z09: [18.9295, 72.8365], // Gateway of India / Taj Palace
  Z10: [18.9345, 72.8340], // Kala Ghoda Arts District
  Z11: [18.9435, 72.8400], // Ballard Estate / Port Trust
  Z12: [18.9285, 72.8200], // Nariman Point Coastal / NCPA
  Z13: [18.9245, 72.8335], // Radio Club / East Promenade
  Z14: [18.9245, 72.8190], // Cuffe Parade North / WTC
  Z15: [18.9170, 72.8285], // Sassoon Docks / East Harbor
  Z16: [18.9155, 72.8210], // Colaba Market / Post Office
  Z17: [18.9090, 72.8185], // Old Navy Nagar East / Holiday Camp
  Z18: [18.9065, 72.8125], // Navy Nagar West / TIFR Coastal
  Z19: [18.9020, 72.8150], // Navy Nagar South / INS Kunjali
  Z20: [18.8960, 72.8130], // Menaka / Southern Peninsula Tip
  Z21: [18.9135, 72.8140], // Afghan Church / Dandi West
};

function getZoneLatLng(zone: Zone): [number, number] {
  if (zone.coordinates?.lat && zone.coordinates?.lng) {
    return [zone.coordinates.lat, zone.coordinates.lng];
  }
  if (MUMBAI_ZONE_GEO[zone.id]) {
    return MUMBAI_ZONE_GEO[zone.id];
  }
  const normX = zone.center_normalized?.x ?? 0.5;
  const normY = zone.center_normalized?.y ?? 0.5;
  return [18.896 + normY * 0.048, 72.812 + normX * 0.028];
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
  const circlesMapRef = useRef<Map<string, L.Circle>>(new Map());
  const hasFittedBoundsRef = useRef<boolean>(false);

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

    // Centered on South Mumbai peninsula (Menaka to Ballard Estate)
    const map = L.map(mapContainerRef.current, {
      center: [18.922, 72.827],
      zoom: 14,
      zoomControl: false,
      attributionControl: true,
    });

    // Free, zero-API-key basemap options:
    // 1. ArcGIS Dark Gray Base + Labels (default: matches cyber command-center aesthetic)
    const esriDarkBase = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      {
        maxNativeZoom: 16,
        maxZoom: 19,
        attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
      }
    );

    const esriDarkRef = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
      {
        maxNativeZoom: 16,
        maxZoom: 19,
      }
    );

    const esriDarkGroup = L.layerGroup([esriDarkBase, esriDarkRef]);

    // 2. OpenStreetMap Standard (100% free open street map)
    const osmLayer = L.tileLayer(
      'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }
    );

    // Add Esri Dark by default
    esriDarkGroup.addTo(map);

    // Layer switcher control for operator convenience
    L.control
      .layers(
        {
          'Tactical Dark (Esri)': esriDarkGroup,
          'OpenStreetMap (Streets)': osmLayer,
        },
        undefined,
        { position: 'topright' }
      )
      .addTo(map);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;
    layerGroupRef.current = layerGroup;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      layerGroupRef.current = null;
      circlesMapRef.current.clear();
      hasFittedBoundsRef.current = false;
    };
  }, []);

  // 4. Render and update Zone Overlays & Flood Contours in-place
  useEffect(() => {
    const layerGroup = layerGroupRef.current;
    if (!layerGroup || zones.length === 0) return;

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

    const circlesMap = circlesMapRef.current;

    // Check if zone list count changed; if so, clear layers
    if (circlesMap.size !== zones.length) {
      layerGroup.clearLayers();
      circlesMap.clear();
    }

    zones.forEach((zone) => {
      const [lat, lng] = getZoneLatLng(zone);

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

      const strokeColor = isSelected ? '#38bdf8' : isSurcharging ? '#f97316' : color;
      const weight = isSelected ? 3.5 : isSurcharging ? 2.5 : 1.5;
      const dashArray = isSurcharging ? '6, 6' : undefined;
      const fillOpacity = isSelected ? 0.65 : 0.45;

      const shortWard = zone.ward_name ? ` (${zone.ward_name.split('/')[0].trim()})` : '';
      const tooltipContent = `${zone.id}${shortWard}: ${depthCm} cm`;

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

      let circle = circlesMap.get(zone.id);
      if (!circle) {
        circle = L.circle([lat, lng], {
          radius: 280,
          color: strokeColor,
          weight,
          dashArray,
          fillColor: color,
          fillOpacity,
        });

        circle.bindTooltip(tooltipContent, {
          permanent: true,
          direction: 'center',
          className: 'gis-zone-tooltip',
        });

        circle.on('click', () => {
          setSelectedZoneId(zone.id);
        });

        circle.bindPopup(popupHtml);
        layerGroup.addLayer(circle);
        circlesMap.set(zone.id, circle);
      } else {
        circle.setStyle({
          color: strokeColor,
          weight,
          dashArray,
          fillColor: color,
          fillOpacity,
        });
        circle.setTooltipContent(tooltipContent);
        circle.setPopupContent(popupHtml);
      }
    });

    // Auto-fit map viewport to encompass all 21 peninsula zones
    if (circlesMap.size > 0 && !hasFittedBoundsRef.current && mapInstanceRef.current) {
      const circleList = Array.from(circlesMap.values());
      const group = L.featureGroup(circleList);
      mapInstanceRef.current.fitBounds(group.getBounds(), { padding: [20, 20] });
      hasFittedBoundsRef.current = true;
    }
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
            <span>Safe Zones</span>
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
