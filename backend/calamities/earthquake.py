from typing import Any, Dict, List, Optional

from core.enums import CalamityType

from calamities.base import Calamity

from algorithms.earthquake.intensity import SeismicEngine
from algorithms.earthquake.damage import SeismicDamageEngine


class Earthquake(Calamity):
    """
    SATARK earthquake calamity.

    Coordinates the existing:
        - SeismicEngine
        - SeismicDamageEngine

    The underlying seismic calculations remain inside the
    algorithms package.
    """

    calamity_type = CalamityType.EARTHQUAKE

    def __init__(
        self,
        zone_data: Dict[str, Dict[str, Any]],
        infrastructure_data: List[Dict[str, Any]],
        epicenter_lat: float,
        epicenter_lon: float,
        magnitude: float,
        depth_km: float,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(parameters)

        if magnitude <= 0:
            raise ValueError(
                "Earthquake magnitude must be greater than 0."
            )

        if depth_km < 0:
            raise ValueError(
                "Earthquake depth cannot be negative."
            )

        self.zone_data = zone_data
        self.infrastructure_data = infrastructure_data

        self.epicenter_lat = epicenter_lat
        self.epicenter_lon = epicenter_lon

        self.magnitude = magnitude
        self.depth_km = depth_km

        self.intensity_engine: (
            Optional[SeismicEngine]
        ) = None

        self.damage_engine: (
            Optional[SeismicDamageEngine]
        ) = None

    def initialize(self) -> None:
        """
        Initialize the seismic calculation engines.
        """
        self.intensity_engine = SeismicEngine(
            self.zone_data
        )

        self.damage_engine = SeismicDamageEngine(
            self.zone_data,
            self.infrastructure_data,
        )

        self._state = {
            "calamity_type": self.calamity_type.value,
            "magnitude": self.magnitude,
            "depth_km": self.depth_km,
            "epicenter": {
                "latitude": self.epicenter_lat,
                "longitude": self.epicenter_lon,
            },
            "pga": {},
            "damage": {},
        }

        self._initialized = True

    def step(
        self,
        delta_time: float,
    ) -> Dict[str, Any]:
        """
        Calculate earthquake intensity and structural damage.

        The current earthquake algorithms are event-based, so each
        step evaluates the configured earthquake event.
        """
        self._require_initialized()

        if delta_time < 0:
            raise ValueError(
                "delta_time cannot be negative."
            )

        if self.intensity_engine is None:
            raise RuntimeError(
                "Earthquake intensity engine is unavailable."
            )

        if self.damage_engine is None:
            raise RuntimeError(
                "Earthquake damage engine is unavailable."
            )

        pga_map = (
            self.intensity_engine.calculate_pga(
                epicenter_lat=self.epicenter_lat,
                epicenter_lon=self.epicenter_lon,
                magnitude=self.magnitude,
                depth_km=self.depth_km,
            )
        )

        damage_map = (
            self.damage_engine.calculate_structural_damage(
                pga_map
            )
        )

        self._state = {
            "calamity_type": self.calamity_type.value,
            "magnitude": self.magnitude,
            "depth_km": self.depth_km,
            "epicenter": {
                "latitude": self.epicenter_lat,
                "longitude": self.epicenter_lon,
            },
            "pga": dict(pga_map),
            "damage": damage_map,
        }

        return self.state

    def reset(self) -> None:
        """
        Reset the earthquake calamity.
        """
        super().reset()

        self.intensity_engine = None
        self.damage_engine = None
