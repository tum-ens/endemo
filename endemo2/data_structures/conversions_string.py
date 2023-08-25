from __future__ import annotations

from endemo2.data_structures.enumerations import DemandType, HouseholdsSubsectorId, TrafficType, TransportModal

map_demand_to_string = {DemandType.ELECTRICITY: "electricity",
                        DemandType.HEAT: "heat",
                        DemandType.HYDROGEN: "hydrogen"}

map_hh_subsector_to_string = {
    HouseholdsSubsectorId.SPACE_HEATING: "space_heating",
    HouseholdsSubsectorId.SPACE_COOLING: "space_cooling",
    HouseholdsSubsectorId.WATER_HEATING: "water_heating",
    HouseholdsSubsectorId.COOKING: "cooking",
    HouseholdsSubsectorId.LIGHTING_AND_APPLIANCES: "light_and_appliances",
    HouseholdsSubsectorId.OTHER: "other"
}

map_tra_traffic_type_to_string = {
    TrafficType.PERSON: "person",
    TrafficType.FREIGHT: "freight"
}

map_tra_modal_to_string = {
    TransportModal.road_rail: "road_rail",
    TransportModal.road_rail_ship: "road_rail_ship",
    TransportModal.road: "road",
    TransportModal.rail: "rail",
    TransportModal.bus: "bus",
    TransportModal.car: "car",
    TransportModal.ship: "ship"

}
