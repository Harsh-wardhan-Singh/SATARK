from __future__ import annotations

import math
from typing import NamedTuple


class FlowResult(NamedTuple):
    conveyed_flow: float
    surcharge_flow: float
    utilization: float
    is_surcharging: bool


class ManningHydraulicsEngine:
    """
    Physical hydraulics calculation engine based on the empirical Manning formula.
    Governs pipe full-flow discharge capacities, gravity transport, and surcharge.
    """

    DEFAULT_CONCRETE_ROUGHNESS: float = 0.013
    MIN_HYDRAULIC_SLOPE: float = 0.0005

    @classmethod
    def calculate_pipe_capacity(
        cls,
        diameter_m: float,
        slope: float,
        roughness: float = DEFAULT_CONCRETE_ROUGHNESS,
    ) -> float:
        """
        Calculate full-pipe volumetric discharge capacity Q_cap (m^3/s) using Manning's equation:
            Q_cap = (1 / n) * A * (R_h)^(2/3) * S^(1/2)

        Args:
            diameter_m: Internal pipe diameter in meters.
            slope: Longitudinal bed slope (dz / L). Must be non-negative.
            roughness: Manning's n roughness coefficient (e.g. 0.013 for concrete).

        Returns:
            Max volumetric flow capacity in cubic meters per second (m^3/s).
        """
        if diameter_m <= 0.0:
            raise ValueError(f"Pipe diameter must be positive, got {diameter_m}")
        if roughness <= 0.0:
            raise ValueError(f"Manning roughness n must be positive, got {roughness}")

        effective_slope = max(cls.MIN_HYDRAULIC_SLOPE, abs(slope))

        # Full pipe circular geometry
        area = (math.pi * (diameter_m ** 2)) / 4.0
        hydraulic_radius = diameter_m / 4.0

        # Manning equation: Q = (1 / n) * A * (R_h)^(2/3) * (S)^(1/2)
        q_capacity = (
            (1.0 / roughness)
            * area
            * (hydraulic_radius ** (2.0 / 3.0))
            * math.sqrt(effective_slope)
        )
        return float(q_capacity)

    @classmethod
    def calculate_velocity(
        cls,
        discharge_m3_s: float,
        diameter_m: float,
    ) -> float:
        """Calculate mean cross-sectional flow velocity V (m/s)."""
        if diameter_m <= 0.0:
            return 0.0
        area = (math.pi * (diameter_m ** 2)) / 4.0
        return float(discharge_m3_s / area)

    @classmethod
    def evaluate_pipe_flow(
        cls,
        inflow_m3_s: float,
        capacity_m3_s: float,
        pump_boost_m3_s: float = 0.0,
    ) -> FlowResult:
        """
        Determine how much flow a pipe can carry vs how much surcharges.

        Args:
            inflow_m3_s: Water volume entering the pipe per second.
            capacity_m3_s: Gravity full-flow capacity of the pipe.
            pump_boost_m3_s: Additional discharge rate provided by mechanical pumps.

        Returns:
            FlowResult namedtuple containing conveyed flow, surcharge flow, utilization, and surcharge flag.
        """
        effective_capacity = max(0.0, capacity_m3_s + pump_boost_m3_s)

        if effective_capacity <= 0.0:
            return FlowResult(
                conveyed_flow=0.0,
                surcharge_flow=max(0.0, inflow_m3_s),
                utilization=1.0 if inflow_m3_s > 0 else 0.0,
                is_surcharging=inflow_m3_s > 0,
            )

        conveyed = min(inflow_m3_s, effective_capacity)
        surcharge = max(0.0, inflow_m3_s - effective_capacity)
        utilization = min(1.0, inflow_m3_s / effective_capacity)
        is_surcharging = surcharge > 1e-6

        return FlowResult(
            conveyed_flow=float(conveyed),
            surcharge_flow=float(surcharge),
            utilization=float(utilization),
            is_surcharging=is_surcharging,
        )
