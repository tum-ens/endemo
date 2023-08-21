from endemo2.data_structures.containers import Demand
from endemo2.input_and_settings.input_households import HouseholdsSubsectorId
from endemo2.model_instance.instance_filter.households_instance_filter import HouseholdsInstanceFilter
from endemo2.model_instance.model.households.hh_subsectors import HouseholdsSubsector, HotWater, SpaceHeating
from endemo2.model_instance.model.sector import Sector


class Households(Sector):

    def __init__(self, country_name: str, households_instance_filter: HouseholdsInstanceFilter):
        super().__init__()

        # create subsectors
        subsector_ids = households_instance_filter.get_subsectors()

        self.subsectors = dict[HouseholdsSubsectorId, HouseholdsSubsector]()
        for subsector_id in subsector_ids:
            if subsector_id in [HouseholdsSubsectorId.SPACE_COOLING,
                                HouseholdsSubsectorId.LIGHTING_AND_APPLIANCES,
                                HouseholdsSubsectorId.COOKING]:
                self.subsectors[subsector_id] = \
                    HouseholdsSubsector(country_name, subsector_id, households_instance_filter)
            if subsector_id == HouseholdsSubsectorId.WATER_HEATING:
                self.subsectors[subsector_id] = HotWater(country_name, subsector_id, households_instance_filter)
            if subsector_id == HouseholdsSubsectorId.SPACE_HEATING:
                self.subsectors[subsector_id] = SpaceHeating(country_name, subsector_id, households_instance_filter)

    def calculate_demand(self) -> Demand:

        demand = Demand()

        # sum over all subsectors
        for subsector_id, subsector_obj in self.subsectors.items():
            demand.add(subsector_obj.calculate_demand())

        return demand
