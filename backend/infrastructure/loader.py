import json
from pathlib import Path
from typing import Any, Dict, List

from core.types import Position

from infrastructure.building import Building
from infrastructure.facility import Facility
from infrastructure.manager import InfrastructureManager
from infrastructure.road import Road


class InfrastructureLoader:
    """
    Loads SATARK infrastructure data into the Digital Twin.

    This class converts static JSON infrastructure information into
    live infrastructure entities.

    It does not:
        - simulate infrastructure damage
        - calculate cascades
        - calculate risk
        - modify disaster state
        - maintain a separate world state
    """

    def __init__(
        self,
        infrastructure_path: str | Path,
        zone_mapping_path: str | Path,
    ) -> None:
        self.infrastructure_path = Path(
            infrastructure_path
        )

        self.zone_mapping_path = Path(
            zone_mapping_path
        )

    def load(
        self,
        manager: InfrastructureManager,
    ) -> List[object]:
        """
        Load infrastructure JSON and register the resulting entities
        with the supplied InfrastructureManager.

        Returns:
            List of infrastructure entities that were created.
        """
        infrastructure_data = self._load_json(
            self.infrastructure_path
        )

        zone_mapping_data = self._load_json(
            self.zone_mapping_path
        )

        zone_positions = self._build_zone_positions(
            zone_mapping_data
        )

        entities: List[object] = []

        for node in infrastructure_data.get(
            "infrastructure",
            []
        ):
            entity = self._build_entity(
                node,
                zone_positions,
            )

            if entity is None:
                continue

            self._register(
                manager,
                entity,
            )

            entities.append(entity)

        return entities

    def _build_entity(
        self,
        node: Dict[str, Any],
        zone_positions: Dict[str, Position],
    ):
        """
        Convert one raw infrastructure node into a Twin entity.
        """
        node_id = node["id"]
        node_type = str(
            node.get("type", "")
        ).lower()

        zone_id = node["zone_id"]

        if zone_id not in zone_positions:
            raise ValueError(
                f"Infrastructure node '{node_id}' "
                f"references unknown zone '{zone_id}'."
            )

        position = zone_positions[zone_id]

        if self._is_road(node_type):
            return Road(
                id=node_id,
                position=position,
            )

        if self._is_facility(node_type):
            return Facility(
                id=node_id,
                position=position,
                facility_type=self._facility_type(
                    node_type
                ),
            )

        return Building(
            id=node_id,
            position=position,
        )

    def _register(
        self,
        manager: InfrastructureManager,
        entity,
    ) -> None:
        """
        Register an entity using the correct manager operation.
        """
        if isinstance(entity, Road):
            manager.add_road(entity)
            return

        if isinstance(entity, Facility):
            manager.add_facility(entity)
            return

        if isinstance(entity, Building):
            manager.add_building(entity)
            return

        raise TypeError(
            f"Unsupported infrastructure entity type: "
            f"{type(entity).__name__}"
        )

    @staticmethod
    def _build_zone_positions(
        zone_mapping_data: Dict[str, Any],
    ) -> Dict[str, Position]:
        """
        Build representative positions from zone center coordinates.
        """
        positions: Dict[str, Position] = {}

        for zone in zone_mapping_data.get(
            "zones",
            []
        ):
            zone_id = zone["id"]

            center = zone["center_world"]

            positions[zone_id] = Position(
                x=float(center["x"]),
                y=0.0,
                z=float(center["z"]),
            )

        return positions

    @staticmethod
    def _facility_type(
        node_type: str,
    ) -> str:
        """
        Convert raw infrastructure types into Facility categories.
        """
        if node_type == "medical":
            return "HOSPITAL"

        if node_type in {
            "shelter",
            "safe_center",
        }:
            return "SAFE_CENTER"

        return "GENERAL"

    @staticmethod
    def _is_road(
        node_type: str,
    ) -> bool:
        """
        Determine whether a raw node represents a road.
        """
        return node_type in {
            "road",
            "bridge",
            "transport",
            "transportation",
        }

    @staticmethod
    def _is_facility(
        node_type: str,
    ) -> bool:
        """
        Determine whether a raw node represents an operational facility.
        """
        return node_type in {
            "medical",
            "hospital",
            "shelter",
            "safe_center",
            "emergency",
            "facility",
        }

    @staticmethod
    def _load_json(
        path: Path,
    ) -> Dict[str, Any]:
        """
        Load and parse a JSON file.
        """
        if not path.exists():
            raise FileNotFoundError(
                f"Infrastructure data file not found: {path}"
            )

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)