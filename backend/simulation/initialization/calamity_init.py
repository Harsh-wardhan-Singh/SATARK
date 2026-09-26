"""
Authoritative Calamity & Drainage Initialization Subsystem.

Responsible for initializing:
- Flood calamity (FloodPropagator, water states)
- Hyetograph engine (precipitation intensity curves)
- Critical infrastructure network (ExplainableNetwork)
- Stormwater drainage hydraulics and surface coupling
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Tuple

from calamities.flood import Flood
from algorithms.drainage import (
    DrainageNetwork,
    CoupledDrainageModel,
)
from algorithms.flood.impact import FloodImpactEngine
from algorithms.infrastructure.cascade import ExplainableNetwork
from algorithms.rainfall.hyetograph import HyetographEngine

logger = logging.getLogger(__name__)


class CalamityInitializer:
    """
    Encapsulates setup of flood, drainage, hyetograph, and infrastructure
    subsystems for the SATARK SimulationEngine.
    """

    @staticmethod
    def _resolve_path(p: str | Path) -> Path:
        path = Path(p)
        if path.exists():
            return path
        # Try relative to backend root
        backend_root = Path(__file__).resolve().parent.parent.parent
        cand1 = backend_root / p
        if cand1.exists():
            return cand1
        cand2 = backend_root / "data" / path.name
        if cand2.exists():
            return cand2
        return path

    @classmethod
    def initialize_flood_and_hydraulics(
        cls,
        scenario: Any,
        world: Any,
    ) -> Tuple[
        Flood,
        HyetographEngine,
        dict[str, dict[str, Any]],
        FloodImpactEngine,
        ExplainableNetwork,
        CoupledDrainageModel | None,
    ]:
        zone_mapping_path = scenario.zone_mapping_path
        if not zone_mapping_path:
            raise ValueError("Flood scenarios require the 'zone_mapping_path' parameter.")

        mapping_path = cls._resolve_path(zone_mapping_path)
        if not mapping_path.exists():
            raise FileNotFoundError(f"Flood zone mapping file not found: {mapping_path}")

        flood = Flood(
            zone_mapping_path=mapping_path,
            rainfall_intensity=scenario.rainfall_intensity,
            model_step_seconds=scenario.flood_model_step_seconds,
        )
        flood.initialize()

        flood_state = flood.state
        if flood_state:
            world.state.environment["flood_water_levels"] = dict(
                flood_state.get("water_levels", {})
            )
            world.state.environment["rainfall_intensity"] = scenario.rainfall_intensity

        # Hyetograph Engine
        hyetograph_type = scenario.parameters.get("hyetograph_type", "CONSTANT")
        peak_ratio = float(scenario.parameters.get("peak_ratio", 0.375))
        base_intensity = float(scenario.parameters.get("base_rainfall_intensity", 5.0))
        radar_series = scenario.parameters.get("radar_series", None)

        hyetograph = HyetographEngine(
            hyetograph_type=hyetograph_type,
            peak_intensity=scenario.rainfall_intensity,
            duration_seconds=scenario.duration,
            peak_ratio=peak_ratio,
            base_intensity=base_intensity,
            radar_series=radar_series,
        )

        flood_zone_data = {
            zone["id"]: zone
            for zone in flood.propagator.zone_data
        }

        flood_impact = FloodImpactEngine()

        # Critical Infrastructure
        infrastructure_path = scenario.infrastructure_path
        if not infrastructure_path:
            raise ValueError("Flood scenarios require the 'infrastructure_path' parameter.")

        infrastructure_file = cls._resolve_path(infrastructure_path)
        if not infrastructure_file.exists():
            raise FileNotFoundError(f"Infrastructure data file not found: {infrastructure_file}")

        infrastructure_network = ExplainableNetwork(str(infrastructure_file))

        # Coupled Drainage
        raw_drainage_path = scenario.parameters.get(
            "drainage_path",
            scenario.parameters.get(
                "drainage_network_path",
                "data/drainage_network.json",
            ),
        )
        drainage_path = cls._resolve_path(raw_drainage_path) if raw_drainage_path else None

        drainage_model: CoupledDrainageModel | None = None
        if drainage_path and Path(drainage_path).exists():
            try:
                network = DrainageNetwork.from_file(drainage_path)
                drainage_model = CoupledDrainageModel(network=network)
                logger.info(
                    "Drainage network initialized with %d nodes and %d pipes.",
                    len(network.nodes),
                    len(network.pipes),
                )
            except Exception as e:
                logger.warning(
                    "Failed to initialize drainage network from %s: %s",
                    drainage_path,
                    e,
                )
                drainage_model = None

        return (
            flood,
            hyetograph,
            flood_zone_data,
            flood_impact,
            infrastructure_network,
            drainage_model,
        )
