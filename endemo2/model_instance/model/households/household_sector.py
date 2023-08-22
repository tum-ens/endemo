from itertools import repeat

from endemo2.data_structures.containers import Demand, Heat
from endemo2.data_structures.enumerations import DemandType
from endemo2.input_and_settings.input_households import HouseholdsSubsectorId
from endemo2.model_instance.instance_filter.households_instance_filter import HouseholdsInstanceFilter
from endemo2.model_instance.model.households.hh_subsectors import HouseholdsSubsector, HotWater, SpaceHeating
from endemo2.model_instance.model.sector import Sector
from endemo2 import utility as uty


class Households(Sector):

    def __init__(self, country_name: str, households_instance_filter: HouseholdsInstanceFilter):
        super().__init__()

        self.hh_if = households_instance_filter
        self.country_name = country_name

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

    def calculate_demand_distributed_by_nuts2(self) -> dict[str, Demand]:

        demand = self.calculate_demand()
        nuts2_distribution = self.hh_if.get_nuts2_distribution(self.country_name)
        return uty.multiply_dictionary_with_demand(nuts2_distribution, demand)

    def calculate_hourly_demand_efh(self) -> dict[DemandType, [float]]:
        """ per subsectors, but isnt this super iefficient? todo
        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = list(repeat(0.0, 8760))
        res_dict[DemandType.HEAT] = list(repeat(Heat(), 8760))
        res_dict[DemandType.HYDROGEN] = list(repeat(0.0, 8760))

        for subsector_name, subsector in self.subsectors.items():
            subsector_hourly_demand = subsector.calculate_hourly_demand_efh()
            res_dict[DemandType.ELECTRICITY] = \
                [res_value + new_value for (res_value, new_value)
                 in list(zip(res_dict[DemandType.ELECTRICITY], subsector_hourly_demand[DemandType.ELECTRICITY]))]
            res_dict[DemandType.HEAT] = \
                [res_value.copy_add(new_value) for (res_value, new_value)
                 in list(zip(res_dict[DemandType.HEAT], subsector_hourly_demand[DemandType.HEAT]))]
            res_dict[DemandType.HYDROGEN] = \
                [res_value + new_value for (res_value, new_value)
                 in list(zip(res_dict[DemandType.HYDROGEN], subsector_hourly_demand[DemandType.HYDROGEN]))]
        return res_dict
        """
        efh_share = self.hh_if.get_single_household_share()
        hourly_profile: dict[DemandType, [float]] = self.hh_if.get_load_profile_efh()
        demand_efh = self.calculate_demand().copy_scale(efh_share)

        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = [demand_efh.electricity * hour_perc
                                            for hour_perc in hourly_profile[DemandType.ELECTRICITY]]
        res_dict[DemandType.HEAT] = [demand_efh.heat.copy_multiply(hour_perc)
                                     for hour_perc in hourly_profile[DemandType.HEAT]]
        res_dict[DemandType.HYDROGEN] = [demand_efh.hydrogen * hour_perc
                                         for hour_perc in hourly_profile[DemandType.HYDROGEN]]
        return res_dict

    def calculate_hourly_demand_mfh(self) -> dict[DemandType, [float]]:
        """ todo
        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = list(repeat(0.0, 8760))
        res_dict[DemandType.HEAT] = list(repeat(Heat(), 8760))
        res_dict[DemandType.HYDROGEN] = list(repeat(0.0, 8760))

        for subsector_name, subsector in self.subsectors.items():
            subsector_hourly_demand = subsector.calculate_hourly_demand_mfh()
            res_dict[DemandType.ELECTRICITY] = \
                [res_value + new_value for (res_value, new_value)
                 in list(zip(res_dict[DemandType.ELECTRICITY], subsector_hourly_demand[DemandType.ELECTRICITY]))]
            res_dict[DemandType.HEAT] = \
                [res_value.copy_add(new_value) for (res_value, new_value)
                 in list(zip(res_dict[DemandType.HEAT], subsector_hourly_demand[DemandType.HEAT]))]
            res_dict[DemandType.HYDROGEN] = \
                [res_value + new_value for (res_value, new_value)
                 in list(zip(res_dict[DemandType.HYDROGEN], subsector_hourly_demand[DemandType.HYDROGEN]))]
        return res_dict
        """
        mfh_share = 1 - self.hh_if.get_single_household_share()
        hourly_profile: dict[DemandType, [float]] = self.hh_if.get_load_profile_mfh()
        demand_mfh = self.calculate_demand().copy_scale(mfh_share)

        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = [demand_mfh.electricity * hour_perc
                                            for hour_perc in hourly_profile[DemandType.ELECTRICITY]]
        res_dict[DemandType.HEAT] = [demand_mfh.heat.copy_multiply(hour_perc)
                                     for hour_perc in hourly_profile[DemandType.HEAT]]
        res_dict[DemandType.HYDROGEN] = [demand_mfh.hydrogen * hour_perc
                                         for hour_perc in hourly_profile[DemandType.HYDROGEN]]
        return res_dict



