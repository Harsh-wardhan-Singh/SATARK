from __future__ import annotations

import math
from enum import Enum
from typing import Any, Sequence


class HyetographType(str, Enum):
    """Temporal rainfall distribution types for urban flood simulations."""
    CONSTANT = "CONSTANT"
    CHICAGO = "CHICAGO"
    SCS_TYPE_II = "SCS_TYPE_II"
    RADAR_NOWCAST = "RADAR_NOWCAST"
    TRIANGULAR = "TRIANGULAR"


class HyetographEngine:
    """
    Authoritative temporal rainfall hyetograph engine.

    Models time-varying rainfall precipitation rates across simulation durations.
    Supports standard urban hydrologic synthetic storms (Chicago Design Storm,
    SCS Type II 24h distribution, Triangular distribution) as well as
    real-time IMD / Doppler radar nowcast observations.
    """

    def __init__(
        self,
        hyetograph_type: HyetographType | str = HyetographType.CONSTANT,
        peak_intensity: float = 45.0,
        duration_seconds: float = 10800.0,  # Default 3 hours
        *,
        peak_ratio: float = 0.375,  # Time to peak ratio (r = tp / T), typically 0.35 - 0.40
        b_parameter: float = 600.0,  # IDF parameter b in seconds (10 min)
        c_parameter: float = 0.75,  # IDF exponent c (0.65 - 0.85)
        radar_series: Sequence[tuple[float, float]] | None = None,
        base_intensity: float = 5.0,
    ) -> None:
        if isinstance(hyetograph_type, str):
            try:
                self.hyetograph_type = HyetographType(hyetograph_type.upper())
            except ValueError:
                self.hyetograph_type = HyetographType.CONSTANT
        else:
            self.hyetograph_type = hyetograph_type

        self.peak_intensity = max(0.0, float(peak_intensity))
        self.duration_seconds = max(1.0, float(duration_seconds))
        self.peak_ratio = min(max(0.01, float(peak_ratio)), 0.99)
        self.b_parameter = max(1.0, float(b_parameter))
        self.c_parameter = min(max(0.1, float(c_parameter)), 0.99)
        self.base_intensity = max(0.0, float(base_intensity))

        # Peak time in seconds
        self.time_to_peak = self.duration_seconds * self.peak_ratio

        # Sorted radar points [(t0, i0), (t1, i1), ...]
        self.radar_series: list[tuple[float, float]] = []
        if radar_series:
            sorted_radar = sorted(radar_series, key=lambda p: p[0])
            self.radar_series = [(float(t), max(0.0, float(i))) for t, i in sorted_radar]

    def get_intensity(self, elapsed_seconds: float) -> float:
        """
        Compute instantaneous rainfall intensity (e.g. mm/hr or configured units)
        at the specified elapsed simulation time in seconds.
        """
        t = max(0.0, float(elapsed_seconds))

        if self.hyetograph_type == HyetographType.CONSTANT:
            return self._intensity_constant(t)
        elif self.hyetograph_type == HyetographType.CHICAGO:
            return self._intensity_chicago(t)
        elif self.hyetograph_type == HyetographType.SCS_TYPE_II:
            return self._intensity_scs_type_ii(t)
        elif self.hyetograph_type == HyetographType.RADAR_NOWCAST:
            return self._intensity_radar(t)
        elif self.hyetograph_type == HyetographType.TRIANGULAR:
            return self._intensity_triangular(t)
        else:
            return self._intensity_constant(t)

    def _intensity_constant(self, t: float) -> float:
        if t <= self.duration_seconds:
            return self.peak_intensity
        # Decay gently after storm duration ends
        decay = math.exp(-(t - self.duration_seconds) / 1800.0)
        return max(0.0, self.peak_intensity * decay)

    def _intensity_chicago(self, t: float) -> float:
        """
        Keifer and Chu (1957) Chicago Design Storm formulation.
        Produces an asymmetric bell curve peaking at t = time_to_peak.
        """
        if t > self.duration_seconds * 1.5:
            # Storm dissipated
            return 0.0

        r = self.peak_ratio
        tp = self.time_to_peak
        b = self.b_parameter
        c = self.c_parameter

        if t <= tp:
            # Rising limb: tr = (tp - t) / r
            tr = (tp - t) / r
            ratio = b / (tr + b)
            # Factor ensures peak is at t = tp
            factor = (ratio ** c) * (1.0 - (c * tr) / (tr + b))
        else:
            # Falling limb: tf = (t - tp) / (1 - r)
            tf = (t - tp) / (1.0 - r)
            ratio = b / (tf + b)
            factor = (ratio ** c) * (1.0 - (c * tf) / (tf + b))

        # Clamp factor and scale between base and peak intensity
        factor = max(0.0, min(1.0, factor))
        return self.base_intensity + (self.peak_intensity - self.base_intensity) * factor

    def _intensity_scs_type_ii(self, t: float) -> float:
        """
        SCS / NRCS Type II 24-hour storm dimensionless distribution derivative.
        Produces a sharp convective peak centered at t / T = 0.5.
        """
        if t > self.duration_seconds * 1.25:
            return 0.0

        tau = t / self.duration_seconds  # Normalized time in [0, 1]
        # High steepness bell centered at tau = 0.5
        d_tau = tau - 0.5
        denom = 1.0 + 36.0 * (d_tau ** 2)
        factor = 1.0 / (denom ** 2)

        return self.base_intensity + (self.peak_intensity - self.base_intensity) * factor

    def _intensity_radar(self, t: float) -> float:
        """Piecewise linear interpolation through Doppler radar observations."""
        if not self.radar_series:
            return self.peak_intensity

        if t <= self.radar_series[0][0]:
            return self.radar_series[0][1]

        if t >= self.radar_series[-1][0]:
            last_t, last_i = self.radar_series[-1]
            # Exponential decay after last radar observation
            decay = math.exp(-(t - last_t) / 1800.0)
            return last_i * decay

        for i in range(len(self.radar_series) - 1):
            t0, i0 = self.radar_series[i]
            t1, i1 = self.radar_series[i + 1]
            if t0 <= t <= t1:
                dt = t1 - t0
                if dt <= 0:
                    return i0
                w = (t - t0) / dt
                return i0 + w * (i1 - i0)

        return self.peak_intensity

    def _intensity_triangular(self, t: float) -> float:
        """Simple triangular storm hydrograph."""
        if t > self.duration_seconds:
            return 0.0

        tp = self.time_to_peak
        if t <= tp:
            frac = t / max(1.0, tp)
            return self.base_intensity + (self.peak_intensity - self.base_intensity) * frac
        else:
            frac = (self.duration_seconds - t) / max(1.0, self.duration_seconds - tp)
            return self.base_intensity + (self.peak_intensity - self.base_intensity) * max(0.0, frac)

    def get_profile(
        self,
        total_seconds: float | None = None,
        step_seconds: float = 60.0,
    ) -> list[dict[str, float]]:
        """
        Generate a discrete time series profile of the rainfall curve.
        """
        duration = total_seconds if total_seconds is not None else self.duration_seconds
        step = max(1.0, float(step_seconds))
        steps = int(duration / step) + 1

        profile: list[dict[str, float]] = []
        for s in range(steps):
            t = s * step
            intensity = self.get_intensity(t)
            profile.append({
                "time_seconds": round(t, 1),
                "time_minutes": round(t / 60.0, 2),
                "time_hours": round(t / 3600.0, 3),
                "intensity": round(intensity, 3),
            })
        return profile

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration parameters into an API-ready dictionary."""
        return {
            "hyetograph_type": self.hyetograph_type.value,
            "peak_intensity": self.peak_intensity,
            "base_intensity": self.base_intensity,
            "duration_seconds": self.duration_seconds,
            "duration_hours": round(self.duration_seconds / 3600.0, 2),
            "peak_ratio": self.peak_ratio,
            "time_to_peak_seconds": self.time_to_peak,
            "radar_points_count": len(self.radar_series),
        }
