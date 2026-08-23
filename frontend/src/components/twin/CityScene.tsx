import React, { useEffect, useRef, useState } from 'react';
import { CityRenderer } from '../../city/CityRenderer';
import { ZoneRenderer } from '../../city/zones/ZoneRenderer';
import { CityStateAdapter } from '../../city/CityStateAdapter';
import { CityInteraction } from '../../city/CityInteraction';
import { fetchZones, fetchSafeZones } from '../../api/worldApi';
import { useStore } from '../../store';
import './CityScene.css';

export const CityScene: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<CityRenderer | null>(null);
  const zoneRendererRef = useRef<ZoneRenderer | null>(null);
  const stateAdapterRef = useRef<CityStateAdapter | null>(null);
  const interactionRef = useRef<CityInteraction | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);

  // Load initial world data
  useEffect(() => {
    const loadWorldData = async () => {
      try {
        const [zones, safeZones] = await Promise.all([
          fetchZones(),
          fetchSafeZones()
        ]);
        useStore.getState().setZones(zones);
        useStore.getState().setSafeZones(safeZones);
      } catch (err) {
        console.error("Failed to load world data:", err);
      }
    };
    loadWorldData();
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;

    // Initialize the renderer only once per mount
    const renderer = new CityRenderer(containerRef.current);
    rendererRef.current = renderer;

    renderer.onProgress = (percent) => {
      setProgress(percent);
    };

    renderer.onLoadComplete = () => {
      setLoading(false);
      
      // Initialize zone layer, interaction, and state sync AFTER city loads
      const zoneRenderer = new ZoneRenderer(renderer);
      zoneRendererRef.current = zoneRenderer;

      const stateAdapter = new CityStateAdapter(zoneRenderer);
      stateAdapterRef.current = stateAdapter;

      const interaction = new CityInteraction(containerRef.current!, renderer, zoneRenderer);
      interactionRef.current = interaction;
    };

    renderer.onError = (err) => {
      console.error("Renderer failed to load assets:", err);
    };

    renderer.load();

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.target === containerRef.current) {
          const { width, height } = entry.contentRect;
          renderer.resize(width, height);
        }
      }
    });

    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      interactionRef.current?.dispose();
      stateAdapterRef.current?.dispose();
      zoneRendererRef.current?.dispose();
      renderer.dispose();
      
      interactionRef.current = null;
      stateAdapterRef.current = null;
      zoneRendererRef.current = null;
      rendererRef.current = null;
    };
  }, []);

  return (
    <div className="city-scene-container" ref={containerRef}>
      {loading && (
        <div className="city-scene-loading">
          Loading city.glb... {progress.toFixed(0)}%
        </div>
      )}
    </div>
  );
};
