
from endemo2.data_structures.containers import Demand, Heat
from endemo2.data_structures.enumerations import DemandType
from endemo2.data_structures.conversions_unit import Unit, convert
from endemo2.input_and_settings.input_households import HouseholdsSubsectorId
from endemo2.model_instance.instance_filter.households_instance_filter import HouseholdsInstanceFilter
from endemo2 import utility as uty


class HouseholdsSubsector:
    """
    The CtsSubsector represents a subsector of the Commercial Trades and Services sector.

    :ivar str _country_name: The name of the country this subsector belongs to.
    :ivar str _subsector_name: The name of the subsector.
    :ivar CtsInstanceFilter _cts_if: The instance filter of the cts sector.
    """
    def __init__(self, country_name: str, subsector_id: HouseholdsSubsectorId, hh_if: HouseholdsInstanceFilter):
        self._country_name = country_name
        self._subsector_id = subsector_id
        self._hh_if = hh_if

    def calculate_demand(self) -> Demand:
        """ Calculate demand for this subsector. """
        # get variables from instance filter
        energy_consumption_in_target_year = \
            self._hh_if.get_energy_consumption_in_target_year(self._country_name, self._subsector_id)
        heat_levels: Heat = self._hh_if.get_heat_levels()

        # get the single demands
        electricity, heat, hydrogen = energy_consumption_in_target_year

        # split heat levels
        heat_in_levels = heat_levels.copy_multiply_scalar(heat)

        return Demand(electricity, heat_in_levels, hydrogen)

    def calculate_demand_distributed_by_nuts2(self) -> dict[str, Demand]:
        """ Calculate demand for this subsector distributed by nuts2 regions. """
        demand = self.calculate_demand()
        nuts2_distribution = self._hh_if.get_nuts2_distribution(self._country_name)
        return uty.multiply_dictionary_with_demand(nuts2_distribution, demand)

    def calculate_hourly_demand_efh(self) -> dict[DemandType, [float]]:
        """ Calculate demand for single person households in this subsector. """
        efh_share = self._hh_if.get_single_household_share()
        hourly_profile: dict[DemandType, [float]] = self._hh_if.get_load_profile_efh()
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
        """ Calculate demand for multiple persons households in this subsector. """
        mfh_share = 1 - self._hh_if.get_single_household_share()
        hourly_profile: dict[DemandType, [float]] = self._hh_if.get_load_profile_mfh()
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
    """
    This class specifies the calculation per equation for the hot water subsector in the households sector.

    :ivar str _country_name: The name of the country this subsector belongs to.
    :ivar str _subsector_name: The name of the subsector.
    :ivar CtsInstanceFilter _cts_if: The instance filter of the cts sector.
    """

    def __init__(self, country_name:str, subsector_id: HouseholdsSubsectorId,  hh_if: HouseholdsInstanceFilter):
        super().__init__(country_name, subsector_id, hh_if)

    # override method
    def calculate_demand(self) -> Demand:
        """ Calculate demand for this subsector. """
        # get variables from instance filter
        liter_per_capita = self._hh_if.get_hot_water_liter_per_capita(self._country_name)
        specific_capacity = self._hh_if.get_hot_water_specific_capacity()
        inlet_temperature = self._hh_if.get_hot_water_inlet_temperature(self._country_name)
        outlet_temperature = self._hh_if.get_hot_water_outlet_temperature()
        calibration_factor = self._hh_if.get_hot_water_calibration_factor(self._country_name)
        population_target_year = self._hh_if.get_population_in_target_year(self._country_name)
        heat_levels: Heat = self._hh_if.get_heat_levels()

        # calculate heat demand
        liter_in_target_year = population_target_year * liter_per_capita
        delta_temperature = convert(Unit.kWh, Unit.TWh, (outlet_temperature - inlet_temperature))   # kWh -> TWh
        heat = liter_in_target_year * specific_capacity * delta_temperature * calibration_factor

        # split in levels
        heat_in_levels = heat_levels.copy_multiply_scalar(heat)

        return Demand(0, heat_in_levels, 0)


class SpaceHeating(HouseholdsSubsector):
    """
    This class specifies the calculation per equation for the space heating subsector in the households sector.

    :ivar str _country_name: The name of the country this subsector belongs to.
    :ivar str _subsector_name: The name of the subsector.
    :ivar CtsInstanceFilter _cts_if: The instance filter of the cts sector.
    """

    def __init__(self, country_name: str, subsector_id: HouseholdsSubsectorId, hh_if: HouseholdsInstanceFilter):
        super().__init__(country_name, subsector_id, hh_if)

    # override method
    def calculate_demand(self) -> Demand:
        """ Calculate demand for this subsector. """
        # get variables from instance filter
        floor_space_in_target_year = self._hh_if.get_area_per_household_in_target_year(self._country_name)
        population_in_target_year = self._hh_if.get_population_in_target_year(self._country_name)
        avg_persons_per_household = self._hh_if.get_avg_persons_per_household_in_target_year(self._country_name)
        specific_heat_in_target_year = self._hh_if.get_space_heating_specific_heat_in_target_year(self._country_name)
        calibration_factor = self._hh_if.get_space_heating_calibration_factor(self._country_name)
        heat_levels: Heat = self._hh_if.get_heat_levels()

        # calculate heat demand
        num_households = population_in_target_year/avg_persons_per_household
        heat = floor_space_in_target_year * num_households * specific_heat_in_target_year * calibration_factor

        # split in levels
        heat_in_levels = heat_levels.copy_multiply_scalar(heat)

        return Demand(0, heat_in_levels, 0)


