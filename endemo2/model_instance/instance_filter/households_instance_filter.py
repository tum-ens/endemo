import warnings

from endemo2.data_structures.containers import Demand, Heat, Interval
from endemo2.data_structures.enumerations import DemandType, ForecastMethod
from endemo2.data_structures.prediction_models import Timeseries, Coef
from endemo2.input_and_settings.control_parameters import ControlParameters
from endemo2.input_and_settings.input_general import GeneralInput
from endemo2.input_and_settings.input_households import HouseholdsInput, HouseholdsSubsectorId
from endemo2.model_instance.instance_filter.general_instance_filter import CountryInstanceFilter
from endemo2.preprocessing.preprocessing_step_one import CountryPreprocessed


class HouseholdsInstanceFilter:

    def __init__(self, ctrl: ControlParameters, general_input: GeneralInput, hh_input: HouseholdsInput,
                 countries_pp: [CountryPreprocessed], country_if: CountryInstanceFilter):
        self.ctrl = ctrl
        self.general_input = general_input
        self.hh_input = hh_input
        self.countries_pp = countries_pp
        self.country_if = country_if

    def get_subsectors(self) -> [HouseholdsSubsectorId]:
        return self.hh_input.hh_subsectors

    def get_energy_consumption_in_target_year(self, country_name, subsector_id: HouseholdsSubsectorId) \
            -> (float, float, float):
        subsector_pp: dict[DemandType, Timeseries] = \
            self.countries_pp[country_name].households_pp.sectors_pp[subsector_id]

        target_year = self.ctrl.general_settings.target_year

        dict_demand = dict[DemandType, float]()
        for demand_type, ts in subsector_pp.items():
            coef = ts.get_coef()
            coef.set_method(ForecastMethod.LINEAR)
            dict_demand[demand_type] = coef.get_function_y(target_year)

        return dict_demand[DemandType.ELECTRICITY], dict_demand[DemandType.HEAT], dict_demand[DemandType.HYDROGEN]

    def get_hot_water_liter_per_capita(self, country_name) -> float:
        hot_water_per_person = self.hh_input.hw_dict_hot_water_per_person_per_day[country_name]
        hot_water_per_person *= 365     # per year
        hot_water_per_person /= 1000    # liter -> m^3
        return hot_water_per_person

    def get_hot_water_specific_capacity(self) -> float:
        return self.hh_input.hw_specific_capacity

    def get_hot_water_inlet_temperature(self, country_name) -> float:
        return self.hh_input.hw_inlet_temperature[country_name]

    def get_hot_water_outlet_temperature(self) -> float:
        return self.hh_input.hw_outlet_temperature

    def get_hot_water_calibration_factor(self, country_name) -> float:
        return self.hh_input.hw_dict_hot_water_calibration[country_name]

    def get_population_in_target_year(self, country_name) -> float:
        return self.country_if.get_population_country_in_target_year(country_name) #todo: change after testing
        #return self.country_if.get_population_nuts2_sum(country_name)

    def get_heat_levels(self) -> Heat:
        return self.ctrl.hh_settings.heat_levels

    def get_area_per_household_in_target_year(self, country_name) -> float:
        start_point, change_rate = self.hh_input.sh_area_per_household[country_name]
        target_year = self.ctrl.general_settings.target_year

        forecast_coef = Coef()
        forecast_coef.set_exp(start_point, change_rate)
        forecast_coef.set_method(ForecastMethod.EXPONENTIAL)

        return forecast_coef.get_function_y(target_year)

    def get_avg_persons_per_household_in_target_year(self, country_name) -> float:
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
        interval = None
        for (x1, y1), (x2, y2) in person_per_household_intervals:
            if target_year < x1 or x2 < target_year:
                # target year is outside current interval -> skip
                continue
            if x1 == target_year:
                # smaller supporting point is at target year -> directly return
                return y1
            if x2 == target_year:
                # larger supporting point is at target year -> directly return
                return y2
            if x1 < target_year < x2:
                # found correct interval -> break loop
                interval = Interval((x1, y1), (x2, y2))

        if interval is None:
            warnings.warn("Target year not within bounds of the average person per household input.")

        # unpack supporting points
        x1, y1 = interval.start
        x2, y2 = interval.end

        # calculate change_rate for exponential growth interpolation
        change_rate = 1 - (y2 / max(0.01, y1)) ** (1 / (x2 - x1))

        # forecast
        forecast_coef = Coef()
        forecast_coef.set_exp(interval.start, change_rate)
        forecast_coef.set_method(ForecastMethod.EXPONENTIAL)

        return forecast_coef.get_function_y(target_year)

    def get_space_heating_specific_heat_in_target_year(self, country_name) -> float:
        start_point, change_rate = self.hh_input.sh_specific_heat[country_name]
        target_year = self.ctrl.general_settings.target_year

        forecast_coef = Coef()
        forecast_coef.set_exp(start_point, change_rate)
        forecast_coef.set_method(ForecastMethod.EXPONENTIAL)

        # do forecast
        forecasted_specific_demand = forecast_coef.get_function_y(target_year)

        # convert unit kWh -> TWh; todo: more pretty conversion
        forecasted_specific_demand /= 10 ** 9

        return forecasted_specific_demand

    def get_space_heating_calibration_factor(self, country_name) -> float:
        return self.hh_input.hw_dict_hot_water_calibration[country_name]  # TODO: is this correct?

    def get_nuts2_distribution(self, country_name) -> dict[str, float]:
        return self.country_if.get_population_nuts2_percentages_in_target_year(country_name)

    def get_single_household_share(self) -> float:
        return self.ctrl.hh_settings.single_households_share

    def get_load_profile_efh(self) -> dict[DemandType, [float]]:
        return self.hh_input.load_profile_single_households

    def get_load_profile_mfh(self) -> dict[DemandType, [float]]:
        return self.hh_input.load_profile_multiple_households
