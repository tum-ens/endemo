import unittest.util
import warnings

from endemo2.data_structures.containers import Demand, Heat, Interval
from endemo2.data_structures.enumerations import DemandType, ForecastMethod
from endemo2.data_structures.prediction_models import Timeseries, Coef
from endemo2.data_structures.conversions_unit import convert, Unit
from endemo2.input_and_settings.control_parameters import ControlParameters
from endemo2.input_and_settings.input_general import GeneralInput
from endemo2.input_and_settings.input_households import HouseholdsInput, HouseholdsSubsectorId, hh_subsectors, \
    hh_visible_subsectors
from endemo2.model_instance.instance_filter.general_instance_filter import CountryInstanceFilter, InstanceFilter
from endemo2.preprocessing.preprocessor import Preprocessor
from endemo2 import utility as uty



class HouseholdsInstanceFilter(InstanceFilter):
    """ The instance filter for the Households sector. """

    def __init__(self, ctrl: ControlParameters, general_input: GeneralInput, hh_input: HouseholdsInput,
                 preprocessor: Preprocessor, country_if: CountryInstanceFilter):
        super().__init__(ctrl, preprocessor)
        self.general_input = general_input
        self.hh_input = hh_input
        self.country_if = country_if

    def get_subsectors(self) -> [HouseholdsSubsectorId]:
        """ Get a list of the Households sector's subsectors. """
        return hh_visible_subsectors

    def get_energy_consumption_in_target_year(self, country_name, subsector_id: HouseholdsSubsectorId) \
            -> (float, float, float):
        """ Get the linear time trend forecast for a subsector in a country. """
        if subsector_id is HouseholdsSubsectorId.LIGHTING_AND_APPLIANCES:
            return self.get_energy_consumption_lighting_and_appliances_in_target_year(country_name)

        subsector_pp: dict[DemandType, Timeseries] = \
            self.preprocessor.countries_pp[country_name].households_pp.sectors_pp[subsector_id]

        # do forecast
        target_year = self.ctrl.general_settings.target_year

        dict_demand = dict[DemandType, float]()
        for demand_type, ts in subsector_pp.items():
            coef = ts.get_coef()
            coef.set_method(ForecastMethod.LINEAR)
            dict_demand[demand_type] = coef.get_function_y(target_year)

        # multiply with population; that way the value is not per capita anymore
        population_in_target_year = self.get_population_in_target_year(country_name)

        for demand_type in [DemandType.ELECTRICITY, DemandType.HEAT, DemandType.HYDROGEN]:
            dict_demand[demand_type] *= population_in_target_year

        return dict_demand[DemandType.ELECTRICITY], dict_demand[DemandType.HEAT], dict_demand[DemandType.HYDROGEN]

    def get_energy_consumption_lighting_and_appliances_in_target_year(self, country_name) -> (float, float, float):
        """ Get the linear time trend forecast for the lighting and appliances subsector. This is special. """
        country_pp = self.preprocessor.countries_pp[country_name]
        lighting_subsector_pp: dict[DemandType, Timeseries] = \
            country_pp.households_pp.sectors_pp[HouseholdsSubsectorId.LIGHTING_AND_APPLIANCES]
        other_subsector_pp: dict[DemandType, Timeseries] = \
            country_pp.households_pp.sectors_pp[HouseholdsSubsectorId.OTHER]

        # do forecast
        target_year = self.ctrl.general_settings.target_year

        dict_demand = dict[DemandType, float]()
        for demand_type, ts_lighting in lighting_subsector_pp.items():
            ts_other = other_subsector_pp[demand_type]

            coef_other = ts_other.get_coef()
            coef_lighting = ts_lighting.get_coef()

            coef_other.set_method(ForecastMethod.LINEAR)
            coef_lighting.set_method(ForecastMethod.LINEAR)

            dict_demand[demand_type] = \
                coef_lighting.get_function_y(target_year) + coef_other.get_function_y(target_year)

        # multiply with population; that way the value is not per capita anymore
        population_in_target_year = self.get_population_in_target_year(country_name)

        for demand_type in [DemandType.ELECTRICITY, DemandType.HEAT, DemandType.HYDROGEN]:
            dict_demand[demand_type] *= population_in_target_year

        return dict_demand[DemandType.ELECTRICITY], dict_demand[DemandType.HEAT], dict_demand[DemandType.HYDROGEN]

    def get_hot_water_liter_per_capita(self, country_name) -> float:
        """ Get the amount of hot water per person in a year in m^3. """
        hot_water_per_person = self.hh_input.hw_dict_hot_water_per_person_per_day[country_name]
        hot_water_per_person *= 365     # per year
        hot_water_per_person = convert(Unit.liter, Unit.m3, hot_water_per_person)    # liter -> m^3
        return hot_water_per_person

    def get_hot_water_specific_capacity(self) -> float:
        """ Get the specific capacity for hot water. """
        return self.hh_input.hw_specific_capacity

    def get_hot_water_inlet_temperature(self, country_name) -> float:
        """ Get the inlet temperature of hot water in a given country. """
        return self.hh_input.hw_inlet_temperature[country_name]

    def get_hot_water_outlet_temperature(self) -> float:
        """ Get the outlet temperature of water. """
        return self.hh_input.hw_outlet_temperature

    def get_hot_water_calibration_factor(self, country_name) -> float:
        """ Get the hot water calibration factor for a given country. """
        return self.hh_input.hw_dict_hot_water_calibration[country_name]

    def get_population_in_target_year(self, country_name) -> float:
        """ Get the population of a country in the target year. """
        return self.country_if.get_population_country_in_target_year(country_name)

    def get_heat_levels(self) -> Heat:
        """ Get the heat levels of the household sector. """
        return self.ctrl.hh_settings.heat_levels

    def get_area_per_household_in_target_year(self, country_name) -> float:
        """ Get the area per household in target year for a given country. """
        start_point, change_rate = self.hh_input.sh_area_per_household[country_name]
        target_year = self.ctrl.general_settings.target_year

        forecast_coef = Coef()
        forecast_coef.set_exp(start_point, change_rate)
        forecast_coef.set_method(ForecastMethod.EXPONENTIAL)

        return forecast_coef.get_function_y(target_year)

    def get_avg_persons_per_household_in_target_year(self, country_name) -> float:
        """ Get average number of persons per household in target year for a given country. """
        person_per_household = self.hh_input.sh_persons_per_household
        target_year = self.ctrl.general_settings.target_year

        # Timeseries without coefficients, if coefficients are needed move to preprocessing.
        person_per_household_historical = Timeseries(person_per_household.historical[country_name])

        # use historical if available
        if target_year <= person_per_household_historical.get_last_data_entry()[0]:
            return person_per_household_historical.get_value_at_year(target_year)

        # do prognosis
        person_per_household_intervals = person_per_household.prognosis[country_name]

        # find correct interval
        interval = uty.find_interval_between_datapoints(person_per_household_intervals, target_year)

        if interval is None:
            warnings.warn("Target year not within bounds of the average person per household input.")

        return uty.exponential_interpolation(interval.start, interval.end, target_year)

    def get_space_heating_specific_heat_in_target_year(self, country_name) -> float:
        """ Get the amount of specific heat for space heating in a given country in TWh. """
        start_point, change_rate = self.hh_input.sh_specific_heat[country_name]
        target_year = self.ctrl.general_settings.target_year

        forecast_coef = Coef()
        forecast_coef.set_exp(start_point, change_rate)
        forecast_coef.set_method(ForecastMethod.EXPONENTIAL)

        # do forecast
        forecasted_specific_demand = forecast_coef.get_function_y(target_year)

        # convert unit kWh -> TWh
        forecasted_specific_demand = convert(Unit.kWh, Unit.TWh, forecasted_specific_demand)

        return forecasted_specific_demand

    def get_space_heating_calibration_factor(self, country_name) -> float:
        """ Get the calibration factor for space heating. """
        return self.hh_input.sh_dict_space_heating_calibration[country_name]

    def get_nuts2_distribution(self, country_name) -> dict[str, float]:
        """ Get the distribution percentages/100 for the nuts2 regions. """
        return self.country_if.get_population_nuts2_percentages_in_target_year(country_name)

    def get_single_household_share(self) -> float:
        """ Get the percentage/100 of the share of single person households."""
        return self.ctrl.hh_settings.single_households_share

    def get_load_profile_efh(self) -> dict[DemandType, [float]]:
        """ Get the load profile for the single person households. """
        return self.hh_input.load_profile_single_households

    def get_load_profile_mfh(self) -> dict[DemandType, [float]]:
        """ Get the load profile for the multiple person households. """
        return self.hh_input.load_profile_multiple_households
