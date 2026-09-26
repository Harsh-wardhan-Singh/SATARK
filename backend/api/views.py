from __future__ import annotations

from pathlib import Path
from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.enums import CalamityType
from core.types import SimulationConfig

from decision.intervention import (
    CandidateIntervention,
    Intervention,
)

from simulation.engine import SimulationEngine
from simulation.scenario import Scenario

import json

from algorithms.navigation import FloodSafeNavigationEngine

from api.serializers import (
    InterventionRequestSerializer,
    NavigationRequestSerializer,
    OptimizationCandidateSerializer,
    SimulationRequestSerializer,
    WorldStateSerializer,
)


_active_engine: SimulationEngine | None = None


def reset_active_engine() -> None:
    global _active_engine
    _active_engine = None


def _require_engine() -> SimulationEngine:
    if _active_engine is None:
        raise RuntimeError(
            "No active simulation exists. "
            "Initialize a simulation first."
        )

    return _active_engine


def _state_payload(
    engine: SimulationEngine,
) -> dict[str, Any]:
    state = WorldStateSerializer(
        engine.world.state
    ).data

    state["simulation"] = {
        "initialized": (
            engine.is_initialized
        ),
        "paused": (
            engine.is_paused
        ),
        "complete": (
            engine.is_complete
        ),
        "duration": (
            engine.scenario.duration
        ),
    }

    state["risk"] = (
        engine.risk_state
    )

    state["recommendations"] = (
        engine.recommendation_state
    )

    state["optimization"] = (
        engine.optimization_state
    )

    state["intervention"] = (
        engine.active_intervention
    )

    state["interventions"] = (
        engine.active_interventions
    )

    state["subsystems"] = {
        "panic": engine.panic_state,
        "evacuation": engine.evacuation_routes,
        "crowd": engine.crowd_state,
        "casualties": engine.casualty_state,
        "infrastructure": (
            engine.infrastructure_state
        ),
    }

    return state


class SimulationInitializeView(
    APIView
):
    """
    Create and initialize one in-memory SATARK SimulationEngine.

    The API owns no simulation state itself; it only retains a reference
    to the current engine instance for HTTP request continuity.
    """

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        global _active_engine

        serializer = (
            SimulationRequestSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        validated = serializer.validated_data

        config = SimulationConfig(
            duration=validated["duration"],
            tick_rate=validated["tick_rate"],
            calamity_type=(
                validated["calamity_type"]
            ),
            random_seed=(
                validated.get(
                    "random_seed"
                )
            ),
        )
        params = dict(validated.get("parameters", {}))
        data_dir = Path(__file__).resolve().parent.parent / "data"
        if "zone_mapping_path" not in params and (data_dir / "glb_zone_mapping.json").exists():
            params["zone_mapping_path"] = str(data_dir / "glb_zone_mapping.json")
        if "infrastructure_path" not in params and (data_dir / "infrastructure.json").exists():
            params["infrastructure_path"] = str(data_dir / "infrastructure.json")
        if "shelters_path" not in params and (data_dir / "shelters.json").exists():
            params["shelters_path"] = str(data_dir / "shelters.json")
        if "population_path" not in params and (data_dir / "population.json").exists():
            params["population_path"] = str(data_dir / "population.json")

        scenario = Scenario(
            config=config,
            initial_state=(
                validated.get(
                    "initial_state",
                    {},
                )
            ),
            parameters=params,
        )

        engine = SimulationEngine(
            scenario=scenario
        )

        engine.initialize()

        _active_engine = engine

        return Response(
            _state_payload(
                engine
            ),
            status=status.HTTP_201_CREATED,
        )


class SimulationStateView(
    APIView
):
    """
    Return the current authoritative simulation state.
    """

    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        try:
            engine = _require_engine()
        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            _state_payload(
                engine
            )
        )


class SimulationStepView(
    APIView
):
    """
    Advance exactly one simulation tick.
    """

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        try:
            engine = _require_engine()

            engine.step()

        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            _state_payload(
                engine
            )
        )


class SimulationRunView(
    APIView
):
    """
    Run the current simulation until its configured duration.
    """

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        try:
            engine = _require_engine()

            while not engine.is_complete:
                engine.step()

        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            _state_payload(
                engine
            )
        )


class SimulationPauseView(
    APIView
):
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        try:
            engine = _require_engine()
            engine.pause()
        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            _state_payload(
                engine
            )
        )


class SimulationResumeView(
    APIView
):
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        try:
            engine = _require_engine()
            engine.resume()
        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            _state_payload(
                engine
            )
        )


class SimulationResetView(
    APIView
):
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        try:
            engine = _require_engine()
            engine.reset()
        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            _state_payload(
                engine
            )
        )


class RiskView(
    APIView
):
    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        try:
            engine = _require_engine()
        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            engine.risk_state
        )


class RecommendationView(
    APIView
):
    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        try:
            engine = _require_engine()
        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "recommendations": (
                    engine.recommendation_state
                )
            }
        )


class OptimizationView(
    APIView
):
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        try:
            engine = _require_engine()
        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )

        candidates_payload = request.data.get(
            "candidates",
            []
        )

        if not isinstance(
            candidates_payload,
            list,
        ):
            return Response(
                {
                    "detail": (
                        "'candidates' must be a list."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OptimizationCandidateSerializer(
            data=candidates_payload,
            many=True,
        )

        serializer.is_valid(
            raise_exception=True
        )

        candidates = []

        for item in serializer.validated_data:

            intervention = Intervention(
                intervention_id=item[
                    "intervention_id"
                ],
                name=item[
                    "name"
                ],
                description=item[
                    "description"
                ],
                priority=item.get(
                    "priority",
                    "MEDIUM",
                ),
                expected_effects=item.get(
                    "expected_effects",
                    {},
                ),
                trigger=item.get(
                    "trigger"
                ),
                source=item.get(
                    "source",
                    "api",
                ),
            )

            candidates.append(
                CandidateIntervention(
                    intervention=intervention,
                    applicable=item.get(
                        "applicable",
                        True,
                    ),
                )
            )

        try:
            result = (
                engine.optimize_interventions(
                    candidates
                )
            )
        except (
            RuntimeError,
            ValueError,
            TypeError,
        ) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            result.to_dict()
        )


class InterventionView(
    APIView
):
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        try:
            engine = _require_engine()
        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = (
            InterventionRequestSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        try:
            result = engine.apply_intervention(
                serializer.validated_data
            )
        except (
            RuntimeError,
            ValueError,
            TypeError,
        ) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        state_payload = _state_payload(engine)
        resp_data = {
            "status": "SUCCESS",
            "intervention": result,
            "state": state_payload,
        }
        resp_data.update(state_payload)
        return Response(resp_data)


class SelectedInterventionView(
    APIView
):
    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        try:
            engine = _require_engine()

            result = (
                engine
                .apply_selected_intervention()
            )

        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        state_payload = _state_payload(engine)
        resp_data = {
            "status": "SUCCESS",
            "intervention": result,
            "state": state_payload,
        }
        resp_data.update(state_payload)
        return Response(resp_data)


class SimulationTeardownView(
    APIView
):
    """
    Tears down the active simulation engine and clears it from server memory.
    """

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        reset_active_engine()
        return Response(
            {
                "status": "SUCCESS",
                "detail": "Simulation engine torn down successfully.",
            },
            status=status.HTTP_200_OK,
        )


class NowcastView(APIView):
    """
    Returns 0-3 hour forward flood nowcast projections across all 21 zones.
    Optional query parameter: ?horizons=1.0,2.0,3.0
    """

    def get(self, request, *args, **kwargs):
        try:
            engine = _require_engine()
        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )

        horizons_param = request.query_params.get("horizons")
        if horizons_param:
            try:
                horizons = [
                    float(h.strip())
                    for h in horizons_param.split(",")
                    if h.strip()
                ]
            except ValueError:
                horizons = [1.0, 2.0, 3.0]
        else:
            horizons = [1.0, 2.0, 3.0]

        try:
            nowcast = engine.generate_nowcast(horizons_hours=horizons)
            return Response(nowcast, status=status.HTTP_200_OK)
        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


_CACHED_WORLD_ZONES: list[dict[str, Any]] | None = None


class WorldZonesView(APIView):
    """
    Returns the authoritative list of 21 simulation zones, their bounds,
    elevation, and neighbor topology.
    """

    def get(self, request, *args, **kwargs):
        global _CACHED_WORLD_ZONES
        if _CACHED_WORLD_ZONES is None:
            data_path = Path(__file__).resolve().parent.parent / "data" / "glb_zone_mapping.json"
            if not data_path.exists():
                return Response(
                    {"detail": "Zone mapping data file not found."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                _CACHED_WORLD_ZONES = data.get("zones", [])

        return Response({"status": "SUCCESS", "count": len(_CACHED_WORLD_ZONES), "zones": _CACHED_WORLD_ZONES})


class WorldSheltersView(APIView):
    """
    Returns municipal emergency shelters, capacities, and assigned zones.
    """

    def get(self, request, *args, **kwargs):
        data_path = Path(__file__).resolve().parent.parent / "data" / "shelters.json"
        if not data_path.exists():
            return Response(
                {"detail": "Shelters data file not found."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            raw_shelters = data.get("shelters", [])

        shelters = []
        for s in raw_shelters:
            item = dict(s)
            item["zoneId"] = s.get("zone_id", s.get("zoneId", ""))
            shelters.append(item)

        return Response({"status": "SUCCESS", "count": len(shelters), "shelters": shelters})


class WorldBoundsView(APIView):
    """
    Returns authoritative world coordinate bounds and axes from glb_zone_mapping.json.
    """

    def get(self, request, *args, **kwargs):
        data_path = Path(__file__).resolve().parent.parent / "data" / "glb_zone_mapping.json"
        if not data_path.exists():
            return Response(
                {"detail": "World mapping data file not found."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            wcs = data.get("world_coordinate_system", {})
            bounds = wcs.get("world_bounds", {})

        return Response({
            "status": "SUCCESS",
            "bounds": bounds,
            "world_coordinate_system": wcs,
        })


class NavigationRouteView(APIView):
    """
    Computes a risk-weighted, flood-safe evacuation/transit route between two zones
    or coordinates, strictly avoiding submerged road segments (>30 cm depth).
    """

    def post(self, request, *args, **kwargs):
        serializer = NavigationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        origin = data.get("origin_zone") or data.get("origin")
        destination = data.get("destination_zone") or data.get("destination")
        allow_flooded = data.get("allow_flooded", False)

        if not origin or not destination:
            return Response(
                {"detail": "Both 'origin' (or 'origin_zone') and 'destination' (or 'destination_zone') are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        global _active_engine
        water_levels_m: dict[str, float] = {}
        panic_scores: dict[str, float] = {}

        if _active_engine is not None and _active_engine.is_initialized:
            water_levels_m = _active_engine.world.state.environment.get("flood_water_levels", {})
            panic_scores = _active_engine.panic_state

        router = FloodSafeNavigationEngine()
        route_result = router.find_route(
            origin=origin,
            destination=destination,
            water_levels_m=water_levels_m,
            panic_scores=panic_scores,
            allow_flooded=allow_flooded,
        )

        return Response(route_result.to_dict(), status=status.HTTP_200_OK)


