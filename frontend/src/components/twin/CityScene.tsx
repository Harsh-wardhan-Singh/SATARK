import React, { useEffect, useRef, useState } from 'react';
import { CityRenderer } from '../../city/CityRenderer';
import './CityScene.css';

export const CityScene: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<CityRenderer | null>(null);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);

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
    };

    renderer.onError = (err) => {
      console.error("Renderer failed to load assets:", err);
      // We could set an error state here if needed
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
      renderer.dispose();
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
