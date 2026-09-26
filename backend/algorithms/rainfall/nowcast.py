from __future__ import annotations

import copy
import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

from algorithms.flood.propagation import FloodPropagator
from algorithms.rainfall.hyetograph import HyetographEngine, HyetographType

logger = logging.getLogger(__name__)


@dataclass
class ZoneNowcastPoint:
    """Nowcast projection metrics for a single zone at a single horizon."""
    zone_id: str
    water_level_m: float
    water_level_cm: float
    delta_cm: float
    is_flooded: bool
    is_critical: bool  # Depth > 30 cm


@dataclass
class HorizonForecast:
    """Projected flood state across all zones at a specific forward horizon."""
    horizon_hours: float
    relative_time_seconds: float
    projected_simulation_time: float
    rainfall_intensity: float
    max_water_level_cm: float
    mean_water_level_cm: float
    flooded_zones_count: int
    critical_zones: list[str] = field(default_factory=list)
    severity_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    water_levels_m: dict[str, float] = field(default_factory=dict)
    water_levels_cm: dict[str, float] = field(default_factory=dict)
    delta_depths_cm: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NowcastEngine:
    """
    Authoritative 0-3 hour forward nowcasting engine for urban flood simulations.

    Forks the active simulation state into an isolated forward-projection branch.
    Simulates coupled rainfall and mass-conserving surface routing across
    t+1h, t+2h, and t+3h horizons without mutating the active world state.
    """

    CRITICAL_DEPTH_CM: float = 30.0  # Impassable road / critical danger threshold

    def __init__(
        self,
        propagator: FloodPropagator,
        hyetograph: HyetographEngine | None = None,
    ) -> None:
        self.base_propagator = propagator
        self.hyetograph = (
            hyetograph
            if hyetograph is not None
            else HyetographEngine(HyetographType.CONSTANT, peak_intensity=45.0)
        )

    def generate_nowcast(
        self,
        current_simulation_time: float,
        horizons_hours: Sequence[float] = (1.0, 2.0, 3.0),
    ) -> dict[str, Any]:
        """
        Generate forward flood projections for the requested hourly horizons.

        Args:
            current_simulation_time: Current authoritative simulation time (seconds).
            horizons_hours: Sequence of forward horizon times in hours (e.g. 1.0, 2.0, 3.0).

        Returns:
            Structured nowcast dictionary containing per-horizon depth projections,
            critical zones, delta depths, and aggregate severity metrics.
        """
        sorted_horizons = sorted(set(max(0.1, float(h)) for h in horizons_hours))
        if not sorted_horizons:
            sorted_horizons = [1.0, 2.0, 3.0]

        # 1. Capture baseline state
        initial_levels_cm = self.base_propagator.get_water_levels_cm()
        initial_max_cm = max(initial_levels_cm.values()) if initial_levels_cm else 0.0

        # 2. Fork simulation state into an independent clone
        cloned_propagator = self.base_propagator.clone()

        forecast_horizons: list[HorizonForecast] = []
        elapsed_forecast_seconds = 0.0
        peak_water_cm = initial_max_cm
        peak_zone_id: str = "Z01"
        all_critical_zones: set[str] = set()

        for horizon in sorted_horizons:
            target_seconds = horizon * 3600.0
            delta_forward_seconds = target_seconds - elapsed_forecast_seconds
            projected_sim_time = current_simulation_time + target_seconds

            # Advance simulation in 1-hour chunks (or remainder)
            hours_to_step = max(1, int(round(delta_forward_seconds / 3600.0)))
            for _ in range(hours_to_step):
                # Query rainfall intensity at this projected forward time
                rain_at_step = self.hyetograph.get_intensity(
                    current_simulation_time + elapsed_forecast_seconds + 3600.0
                )
                cloned_propagator.simulate_hour(rain_at_step)
                elapsed_forecast_seconds += 3600.0

            # Collect projected zone depths
            projected_m = cloned_propagator.get_water_levels_m()
            projected_cm = cloned_propagator.get_water_levels_cm()

            # Compute deltas relative to current baseline
            deltas_cm = {
                zid: round(projected_cm.get(zid, 0.0) - initial_levels_cm.get(zid, 0.0), 2)
                for zid in cloned_propagator.zone_ids
            }

            flooded_count = sum(1 for d in projected_cm.values() if d > 0.0)
            max_depth_cm = max(projected_cm.values()) if projected_cm else 0.0
            mean_depth_cm = (
                sum(projected_cm.values()) / len(projected_cm) if projected_cm else 0.0
            )

            # Identify critical zones (> 30 cm)
            critical = [
                zid for zid, depth in projected_cm.items()
                if depth >= self.CRITICAL_DEPTH_CM
            ]
            all_critical_zones.update(critical)

            for zid, depth in projected_cm.items():
                if depth > peak_water_cm:
                    peak_water_cm = depth
                    peak_zone_id = zid

            # Determine severity classification
            if max_depth_cm >= 60.0:
                severity = "CRITICAL"
            elif max_depth_cm >= 30.0:
                severity = "HIGH"
            elif max_depth_cm >= 15.0:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            rain_now = self.hyetograph.get_intensity(projected_sim_time)

            horizon_forecast = HorizonForecast(
                horizon_hours=float(horizon),
                relative_time_seconds=float(target_seconds),
                projected_simulation_time=round(projected_sim_time, 1),
                rainfall_intensity=round(rain_now, 2),
                max_water_level_cm=round(max_depth_cm, 2),
                mean_water_level_cm=round(mean_depth_cm, 2),
                flooded_zones_count=flooded_count,
                critical_zones=sorted(critical),
                severity_level=severity,
                water_levels_m=projected_m,
                water_levels_cm=projected_cm,
                delta_depths_cm=deltas_cm,
            )
            forecast_horizons.append(horizon_forecast)

        # Determine overall trend
        last_max = forecast_horizons[-1].max_water_level_cm if forecast_horizons else 0.0
        if last_max > initial_max_cm + 1.0:
            trend = "RISING"
        elif last_max < initial_max_cm - 1.0:
            trend = "FALLING"
        else:
            trend = "STABLE"

        return {
            "status": "SUCCESS",
            "current_simulation_time": round(current_simulation_time, 1),
            "baseline_max_water_cm": round(initial_max_cm, 2),
            "hyetograph": self.hyetograph.to_dict(),
            "summary": {
                "peak_projected_water_cm": round(peak_water_cm, 2),
                "peak_zone": peak_zone_id,
                "overall_trend": trend,
                "total_critical_zones_count": len(all_critical_zones),
                "critical_zones": sorted(all_critical_zones),
            },
            "horizons": [h.to_dict() for h in forecast_horizons],
        }
