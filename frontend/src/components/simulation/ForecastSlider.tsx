import React, { useEffect, useState } from 'react';
import { useStore } from '../../store';
import { fetchNowcast, NowcastResponse } from '../../api/simulationApi';
import './ForecastSlider.css';

export const ForecastSlider: React.FC = () => {
  const {
    workflowState,
    environment,
    currentTick,
    forecastHorizonHours,
    setForecastHorizonHours,
  } = useStore();

  const [nowcastData, setNowcastData] = useState<NowcastResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (workflowState !== 'disaster-active') {
      setNowcastData(null);
      setForecastHorizonHours(0);
      return;
    }

    let isMounted = true;
    const loadNowcast = async () => {
      try {
        setLoading(true);
        const res = await fetchNowcast([1.0, 2.0, 3.0]);
        if (isMounted) {
          setNowcastData(res);
        }
      } catch (err) {
        console.warn('Nowcast not available yet:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadNowcast();

    return () => {
      isMounted = false;
    };
  }, [workflowState, currentTick, setForecastHorizonHours]);

  if (workflowState !== 'disaster-active') {
    return null;
  }

  const horizons = [0, 1, 2, 3];

  // Calculate metrics for active horizon
  let maxDepthCm = 0;
  let criticalCount = 0;

  if (forecastHorizonHours === 0) {
    // Current live tick: check if backend already provided direct centimeter levels
    const cmLevels: Record<string, number> =
      (environment as any)?.flood_water_levels_cm || {};
    const cmDepths = Object.values(cmLevels);
    if (cmDepths.length > 0) {
      maxDepthCm = Math.round(Math.max(...cmDepths));
      criticalCount = cmDepths.filter((d) => d >= 30).length;
    } else {
      const waterLevels: Record<string, number> =
        environment?.flood_water_levels || {};
      const depths = Object.values(waterLevels);
      if (depths.length > 0) {
        maxDepthCm = Math.round(Math.max(...depths) * 100);
        criticalCount = depths.filter((d) => d * 100 >= 30).length;
      }
    }
  } else if (nowcastData && nowcastData.horizons) {
    const proj = nowcastData.horizons.find(
      (h) => Math.round(h.horizon_hours) === forecastHorizonHours
    );
    if (proj) {
      const depths = Object.values(proj.water_depth_cm);
      if (depths.length > 0) {
        maxDepthCm = Math.round(Math.max(...depths));
        criticalCount = proj.critical_zones?.length ?? depths.filter((d) => d > 30).length;
      }
    }
  }

  return (
    <div className="forecast-slider-container">
      <div className="forecast-label-group">
        <span className="forecast-title">Nowcast Forecast</span>
        <span className="forecast-subtitle">
          {forecastHorizonHours === 0
            ? `Live Simulation (Hour ${currentTick})`
            : `Projected State at Hour ${currentTick + forecastHorizonHours}`}
        </span>
      </div>

      <div className="forecast-steps-bar">
        {horizons.map((h) => {
          const actualHour = currentTick + h;
          return (
            <button
              key={h}
              className={`forecast-step-btn ${
                forecastHorizonHours === h ? 'active' : ''
              }`}
              onClick={() => setForecastHorizonHours(h)}
              title={
                h === 0
                  ? `Live simulation at Hour ${actualHour}`
                  : `Projected state at Hour ${actualHour}`
              }
            >
              {h === 0 ? (
                <>
                  <span>Hour {actualHour}</span>
                  <span
                    style={{
                      fontSize: '9px',
                      fontWeight: 700,
                      background: 'rgba(16, 185, 129, 0.25)',
                      color: '#34d399',
                      padding: '1px 5px',
                      borderRadius: '3px',
                      marginLeft: '2px',
                    }}
                  >
                    LIVE
                  </span>
                </>
              ) : (
                `Hour ${actualHour}`
              )}
            </button>
          );
        })}
      </div>

      <div className="forecast-metrics">
        <div className="forecast-metric-item">
          <span className="metric-label">Max Depth</span>
          <span className="metric-value">{maxDepthCm} cm</span>
        </div>

        <div className="forecast-metric-item">
          <span className="metric-label">Critical Zones</span>
          {criticalCount > 0 ? (
            <span className="critical-badge">
              ⚠ {criticalCount} Zones (&gt;30cm)
            </span>
          ) : (
            <span className="metric-value" style={{ color: '#10b981' }}>
              0 Zones
            </span>
          )}
        </div>

        {loading && (
          <span style={{ fontSize: '10px', color: '#38bdf8' }}>Syncing...</span>
        )}
      </div>
    </div>
  );
};
