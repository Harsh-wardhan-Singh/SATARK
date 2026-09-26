from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from algorithms.casualties.estimation import CasualtiesEngine
from algorithms.population.crowd import CrowdDynamicsEngine
from algorithms.population.panic import PanicEngine
from algorithms.population.evacuation import EvacuationEngine
from agents.manager import AgentManager
from simulation.scenario import Scenario
from simulation.world import WorldState


class PopulationInitializer:
    """
    Encapsulates human response engines (Panic, Evacuation, Crowd, Casualties)
    and deterministic representative agent cohort initialization.
    """

    @staticmethod
    def _resolve_path(p: str | Path | None) -> Path | None:
        if not p:
            return None
        path = Path(p)
        if path.exists():
            return path
        backend_root = Path(__file__).resolve().parent.parent.parent
        cand1 = backend_root / p
        if cand1.exists():
            return cand1
        cand2 = backend_root / "data" / path.name
        if cand2.exists():
            return cand2
        return path

    @classmethod
    def load_zone_mapping(
        cls,
        scenario: Scenario,
        cached_zone_mapping: dict[str, dict[str, Any]] | None = None,
        flood_zone_data: dict[str, Any] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Loads or returns cached zone mapping.
        """
        if cached_zone_mapping is not None:
            return cached_zone_mapping

        mapping_path = scenario.zone_mapping_path
        if mapping_path:
            path = cls._resolve_path(mapping_path)
        elif flood_zone_data:
            return {str(zid): dict(z) for zid, z in flood_zone_data.items()}
        else:
            raise ValueError("A zone_mapping_path is required for population-agent initialization.")

        if not path or not path.exists():
            raise FileNotFoundError(f"Agent zone mapping file not found: {path}")

        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        zones = data.get("zones")
        if not isinstance(zones, list):
            raise ValueError("Zone mapping must contain a 'zones' list.")

        return {
            str(zone["id"]): dict(zone)
            for zone in zones
            if isinstance(zone, Mapping) and "id" in zone
        }

    @classmethod
    def initialize_human_response(
        cls,
        scenario: Scenario,
        world: WorldState,
        casualty_infrastructure_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Initializes panic, evacuation, crowd dynamics, and casualty engines.
        Returns a dict containing initialized engines and states.
        """
        pop_data = scenario.get_initial_state("population_data")
        pop_path = cls._resolve_path(scenario.population_path)
        if pop_data is None and pop_path and pop_path.exists():
            with open(pop_path, "r", encoding="utf-8") as f:
                pop_data = json.load(f)

        shelter_data = scenario.get_initial_state("shelter_data")
        shelters_path = cls._resolve_path(scenario.shelters_path)
        if shelter_data is None and shelters_path and shelters_path.exists():
            with open(shelters_path, "r", encoding="utf-8") as f:
                shelter_data = json.load(f)

        panic_threshold = float(scenario.get_parameter("panic_threshold", 0.5))
        pop_step_sec = float(scenario.get_parameter("population_model_step_seconds", 1.0))

        if not 0.0 <= panic_threshold <= 1.0:
            raise ValueError("panic_threshold must be between 0.0 and 1.0.")
        if pop_step_sec <= 0:
            raise ValueError("population_model_step_seconds must be greater than 0.")

        if pop_data is None:
            world.state.environment["human_response"] = {
                "enabled": False,
                "reason": "population_data is not configured in Scenario.initial_state.",
                "panic_by_zone": {},
                "evacuation_routes": {},
                "crowd": {},
                "casualties": {},
            }
            return {
                "enabled": False,
                "panic_engine": None,
                "evacuation_engine": None,
                "crowd_engine": None,
                "casualties_engine": None,
                "panic_state": {},
                "evacuation_routes": {},
                "crowd_state": {},
                "casualty_state": {},
                "population_data": None,
                "shelter_data": None,
            }

        if not isinstance(pop_data, Mapping) or "zones" not in pop_data:
            raise ValueError("population_data must be a mapping containing 'zones'.")

        panic_engine = PanicEngine(pop_data)
        panic_state = dict(panic_engine.panic_state)

        if shelter_data is None:
            world.state.environment["human_response"] = {
                "enabled": True,
                "partial": True,
                "panic_by_zone": dict(panic_state),
                "evacuation_routes": {},
                "crowd": {},
                "casualties": {},
            }
            return {
                "enabled": True,
                "panic_engine": panic_engine,
                "evacuation_engine": None,
                "crowd_engine": None,
                "casualties_engine": None,
                "panic_state": panic_state,
                "evacuation_routes": {},
                "crowd_state": {},
                "casualty_state": {},
                "population_data": pop_data,
                "shelter_data": None,
            }

        if not isinstance(shelter_data, Mapping) or "shelters" not in shelter_data:
            raise ValueError("shelter_data must be a mapping containing 'shelters'.")

        zones_path = scenario.get_parameter("zones_path") or scenario.get_parameter("zone_mapping_path")
        shelters_path = scenario.get_parameter("shelters_path")

        evacuation_engine = None
        if zones_path and shelters_path:
            zones_file = cls._resolve_path(zones_path)
            shelters_file = cls._resolve_path(shelters_path)
            if not zones_file or not zones_file.exists():
                raise FileNotFoundError(f"Evacuation zone file not found: {zones_file}")
            if not shelters_file or not shelters_file.exists():
                raise FileNotFoundError(f"Evacuation shelter file not found: {shelters_file}")
            evacuation_engine = EvacuationEngine(
                zones_path=zones_file,
                shelters_path=shelters_file,
            )

        crowd_engine = CrowdDynamicsEngine(
            population_data=pop_data,
            shelter_data=shelter_data,
        )

        casualties_engine = CasualtiesEngine(casualty_infrastructure_data)

        world.state.environment["human_response"] = {
            "enabled": True,
            "panic_by_zone": dict(panic_state),
            "evacuation_routes": {},
            "crowd": {},
            "casualties": {},
        }

        return {
            "enabled": True,
            "panic_engine": panic_engine,
            "evacuation_engine": evacuation_engine,
            "crowd_engine": crowd_engine,
            "casualties_engine": casualties_engine,
            "panic_state": panic_state,
            "evacuation_routes": {},
            "crowd_state": {},
            "casualty_state": {},
            "population_data": pop_data,
            "shelter_data": shelter_data,
        }

    @staticmethod
    def populate_representative_agents(
        scenario: Scenario,
        world: WorldState,
        agent_manager: AgentManager,
        population_data: Any,
        cached_zone_mapping: dict[str, dict[str, Any]],
        clock_tick: int,
    ) -> None:
        """
        Populate the authoritative WorldState with deterministic representative HumanAgent cohorts.
        """
        if population_data is None:
            world.state.environment["population_agents"] = {
                "enabled": False,
                "representative_agent_count": 0,
                "modeled_population": 0.0,
                "zone_population": {},
            }
            return

        representative_count = int(scenario.get_parameter("representative_agent_count", 250))
        agent_speed = float(scenario.get_parameter("agent_speed", 1.0))

        agents = agent_manager.build_population_agents(
            population_data=population_data,
            zone_mapping=cached_zone_mapping,
            representative_agent_count=representative_count,
            default_speed=agent_speed,
        )

        agent_manager.add_agents(agents)
        zone_population = agent_manager.get_zone_population()
        modeled_population = sum(zone_population.values())

        world.state.environment["population_agents"] = {
            "enabled": True,
            "representative_agent_count": len(agents),
            "modeled_population": modeled_population,
            "zone_population": dict(zone_population),
            "representation": "representative_cohorts",
        }

        world.state.update_metric("representative_agent_count", float(len(agents)))
        world.state.update_metric("modeled_population", float(modeled_population))
        world.state.record_event({
            "type": "POPULATION_AGENTS_INITIALIZED",
            "tick": clock_tick,
            "representative_agent_count": len(agents),
            "modeled_population": modeled_population,
        })
