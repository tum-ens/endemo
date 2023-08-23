from __future__ import annotations

from endemo2.data_structures.enumerations import DemandType, HouseholdsSubsectorId

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
