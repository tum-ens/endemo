
from endemo2.data_structures.containers import Demand, Heat
from endemo2.data_structures.enumerations import DemandType
from endemo2.input_and_settings.input_households import HouseholdsSubsectorId
from endemo2.model_instance.instance_filter.households_instance_filter import HouseholdsInstanceFilter
from endemo2 import utility as uty


class HouseholdsSubsector:
    def __init__(self, country_name: str, subsector_id: HouseholdsSubsectorId, hh_if: HouseholdsInstanceFilter):
        self.country_name = country_name
        self.subsector_id = subsector_id
        self.hh_if = hh_if

    def calculate_demand(self) -> Demand:
        # get variables from instance filter
        energy_consumption_in_target_year = \
            self.hh_if.get_energy_consumption_in_target_year(self.country_name, self.subsector_id)
        heat_levels: Heat = self.hh_if.get_heat_levels()

        # get the single demands
        electricity, heat, hydrogen = energy_consumption_in_target_year

        # split heat levels
        heat_in_levels = heat_levels.copy_multiply_scalar(heat)

        return Demand(electricity, heat_in_levels, hydrogen)

    def calculate_demand_distributed_by_nuts2(self) -> dict[str, Demand]:
        demand = self.calculate_demand()
        nuts2_distribution = self.hh_if.get_nuts2_distribution(self.country_name)
        return uty.multiply_dictionary_with_demand(nuts2_distribution, demand)

    def calculate_hourly_demand_efh(self) -> dict[DemandType, [float]]:
        efh_share = self.hh_if.get_single_household_share()
        hourly_profile: dict[DemandType, [float]] = self.hh_if.get_load_profile_efh()
        subsector_demand = self.calculate_demand().copy_scale(efh_share)

        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = [subsector_demand.electricity * hour_perc
                                            for hour_perc in hourly_profile[DemandType.ELECTRICITY]]
        res_dict[DemandType.HEAT] = [subsector_demand.heat.copy_multiply(hour_perc)
                                     for hour_perc in hourly_profile[DemandType.HEAT]]
        res_dict[DemandType.HYDROGEN] = [subsector_demand.hydrogen * hour_perc
                                         for hour_perc in hourly_profile[DemandType.HYDROGEN]]
        return res_dict

    def calculate_hourly_demand_mfh(self) -> dict[DemandType, [float]]:
        mfh_share = 1 - self.hh_if.get_single_household_share()
        hourly_profile: dict[DemandType, [float]] = self.hh_if.get_load_profile_mfh()
        subsector_demand = self.calculate_demand().copy_scale(mfh_share)

        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = [subsector_demand.electricity * hour_perc
                                            for hour_perc in hourly_profile[DemandType.ELECTRICITY]]
        res_dict[DemandType.HEAT] = [subsector_demand.heat.copy_multiply(hour_perc)
                                     for hour_perc in hourly_profile[DemandType.HEAT]]
        res_dict[DemandType.HYDROGEN] = [subsector_demand.hydrogen * hour_perc
                                         for hour_perc in hourly_profile[DemandType.HYDROGEN]]
        return res_dict


class HotWater(HouseholdsSubsector):

    def __init__(self, country_name:str, subsector_id: HouseholdsSubsectorId,  hh_if: HouseholdsInstanceFilter):
        super().__init__(country_name, subsector_id, hh_if)

    # override method
    def calculate_demand(self) -> Demand:
        # get variables from instance filter
        liter_per_capita = self.hh_if.get_hot_water_liter_per_capita(self.country_name)
        specific_capacity = self.hh_if.get_hot_water_specific_capacity()
        inlet_temperature = self.hh_if.get_hot_water_inlet_temperature(self.country_name)
        outlet_temperature = self.hh_if.get_hot_water_outlet_temperature()
        calibration_factor = self.hh_if.get_hot_water_calibration_factor(self.country_name)
        population_target_year = self.hh_if.get_population_in_target_year(self.country_name)
        heat_levels: Heat = self.hh_if.get_heat_levels()

        # calculate heat demand
        liter_in_target_year = population_target_year * liter_per_capita
        delta_temperature = (outlet_temperature - inlet_temperature) / 10**9    # kWh -> TWh todo: prettier
        heat = liter_in_target_year * specific_capacity * delta_temperature * calibration_factor

        # split in levels
        heat_in_levels = heat_levels.copy_multiply_scalar(heat)

        return Demand(0, heat_in_levels, 0)


class SpaceHeating(HouseholdsSubsector):

    def __init__(self, country_name: str, subsector_id: HouseholdsSubsectorId, hh_if: HouseholdsInstanceFilter):
        super().__init__(country_name, subsector_id, hh_if)

    # override method
    def calculate_demand(self) -> Demand:
        # get variables from instance filter
        floor_space_in_target_year = self.hh_if.get_area_per_household_in_target_year(self.country_name)
        population_in_target_year = self.hh_if.get_population_in_target_year(self.country_name)
        avg_persons_per_household = self.hh_if.get_avg_persons_per_household_in_target_year(self.country_name)
        specific_heat_in_target_year = self.hh_if.get_space_heating_specific_heat_in_target_year(self.country_name)
        # calibration_factor = self.hh_if.get_space_heating_calibration_factor(self.country_name) todo remove
        heat_levels: Heat = self.hh_if.get_heat_levels()

        # calculate heat demand
        num_households = population_in_target_year/avg_persons_per_household
        heat = floor_space_in_target_year * num_households * specific_heat_in_target_year # * calibration_factor

        # split in levels
        heat_in_levels = heat_levels.copy_multiply_scalar(heat)

        return Demand(0, heat_in_levels, 0)


