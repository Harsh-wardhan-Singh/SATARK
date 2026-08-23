from typing import List, Optional

from core.enums import InfrastructureStatus
from twin.state import WorldState

from infrastructure.building import Building
from infrastructure.facility import Facility
from infrastructure.road import Road


class InfrastructureManager:
    """
    Manages and queries infrastructure entities stored in the
    authoritative Digital Twin WorldState.

    InfrastructureManager does not maintain a second copy of the world.
    """

    def __init__(self, world_state: WorldState) -> None:
        self.world_state = world_state

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def add_road(self, road: Road) -> None:
        self.world_state.add_entity(road)

    def add_building(self, building: Building) -> None:
        self.world_state.add_entity(building)

    def add_facility(self, facility: Facility) -> None:
        self.world_state.add_entity(facility)

    # -------------------------------------------------------------------------
    # Retrieval
    # -------------------------------------------------------------------------

    def get_road(self, road_id: str) -> Optional[Road]:
        entity = self.world_state.get_entity(road_id)

        if entity is None:
            return None

        if not isinstance(entity, Road):
            raise TypeError(
                f"Entity '{road_id}' is not a Road."
            )

        return entity

    def get_building(
        self,
        building_id: str,
    ) -> Optional[Building]:
        entity = self.world_state.get_entity(building_id)

        if entity is None:
            return None

        if not isinstance(entity, Building):
            raise TypeError(
                f"Entity '{building_id}' is not a Building."
            )

        return entity

    def get_facility(
        self,
        facility_id: str,
    ) -> Optional[Facility]:
        entity = self.world_state.get_entity(facility_id)

        if entity is None:
            return None

        if not isinstance(entity, Facility):
            raise TypeError(
                f"Entity '{facility_id}' is not a Facility."
            )

        return entity

    # -------------------------------------------------------------------------
    # Collections
    # -------------------------------------------------------------------------

    def get_roads(self) -> List[Road]:
        return [
            entity
            for entity in self.world_state.get_entities()
            if isinstance(entity, Road)
        ]

    def get_buildings(self) -> List[Building]:
        return [
            entity
            for entity in self.world_state.get_entities()
            if isinstance(entity, Building)
        ]

    def get_facilities(self) -> List[Facility]:
        return [
            entity
            for entity in self.world_state.get_entities()
            if isinstance(entity, Facility)
        ]

    def get_safe_centers(self) -> List[Facility]:
        return [
            facility
            for facility in self.get_facilities()
            if facility.is_safe_center
            and facility.status == InfrastructureStatus.OPERATIONAL
            and facility.available_capacity > 0
        ]

    # -------------------------------------------------------------------------
    # Status operations
    # -------------------------------------------------------------------------

    def set_road_status(
        self,
        road_id: str,
        status: InfrastructureStatus,
    ) -> None:
        road = self.get_road(road_id)

        if road is None:
            raise KeyError(f"Road '{road_id}' does not exist.")

        road.set_status(status)

    def set_building_status(
        self,
        building_id: str,
        status: InfrastructureStatus,
    ) -> None:
        building = self.get_building(building_id)

        if building is None:
            raise KeyError(
                f"Building '{building_id}' does not exist."
            )

        building.set_status(status)

    def set_facility_status(
        self,
        facility_id: str,
        status: InfrastructureStatus,
    ) -> None:
        facility = self.get_facility(facility_id)

        if facility is None:
            raise KeyError(
                f"Facility '{facility_id}' does not exist."
            )

        facility.set_status(status)

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def clear(self) -> None:
        """
        Remove all infrastructure entities from the authoritative
        WorldState.

        This does not clear unrelated simulation entities such as
        HumanAgent instances.
        """
        for entity in list(self.world_state.get_entities()):
            if isinstance(
                entity,
                (Road, Building, Facility),
            ):
                self.world_state.remove_entity(
                    entity.id
                )