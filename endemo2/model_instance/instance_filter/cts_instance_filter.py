from endemo2.data_structures.containers import SpecConsum, Heat, Demand
from endemo2.data_structures.enumerations import DemandType, ScForecastMethod, ForecastMethod
from endemo2.data_structures.prediction_models import Coef, Timeseries
from endemo2.data_structures.conversions_unit import Unit, convert, get_conversion_scalar
from endemo2.input_and_settings.control_parameters import ControlParameters
from endemo2.input_and_settings.input_cts import CtsInput
from endemo2.input_and_settings.input_general import GeneralInput
from endemo2.model_instance.instance_filter.general_instance_filter import CountryInstanceFilter, InstanceFilter
from endemo2.preprocessing.preprocessing_step_one import CountryPreprocessed, CtsPreprocessed
from endemo2.preprocessing.preprocessor import Preprocessor


class CtsInstanceFilter(InstanceFilter):
    """ The instance filter for the CTS sector. """

    def __init__(self, ctrl: ControlParameters, general_input: GeneralInput, cts_input: CtsInput,
                 preprocessor: Preprocessor, country_if: CountryInstanceFilter):
        super().__init__(ctrl, preprocessor)

        self.general_input = general_input
        self.cts_input = cts_input
        self.country_if = country_if

    def get_cts_subsector_names(self) -> [str]:
        """ Get the names of all _subsectors of the cts sector. """
        return self.cts_input.subsector_names

    def get_specific_consumption(self, country_name) -> SpecConsum:
        """ Get the specific consumption for a country in TWh/thousand employees. """
        cts_pp: CtsPreprocessed = self.preprocessor.countries_pp[country_name].cts_pp
        ts_specific_consumption = cts_pp.specific_consumption

        # get predictions
        target_year = self.ctrl.general_settings.target_year

        sc = dict[DemandType, float]()
        for demand_type in [DemandType.ELECTRICITY, DemandType.HEAT, DemandType.HYDROGEN]:
            sc_ts = ts_specific_consumption[demand_type]
            sc_coef = sc_ts.get_coef()

            # use different forecast methods
            sc_forecast_method = self.ctrl.cts_settings.trend_calc_for_spec
            match sc_forecast_method:
                case ScForecastMethod.LINEAR:
                    sc_coef.set_method(ForecastMethod.LINEAR)
                case ScForecastMethod.LOGARITHMIC:
                    sc_coef.set_method(ForecastMethod.LOGARITHMIC)
                case ScForecastMethod.CONST_MEAN:
                    mean_y = sc_ts.get_mean_y()
                    (last_year, _) = sc_ts.get_last_data_entry()
                    sc_coef.set_exp((last_year, mean_y), 0.0)
                    sc_coef.set_method(ForecastMethod.EXPONENTIAL)
                case ScForecastMethod.CONST_LAST:
                    (last_year, last_value) = sc_ts.get_last_data_entry()
                    sc_coef.set_exp((last_year, last_value), 0.0)
                    sc_coef.set_method(ForecastMethod.EXPONENTIAL)
            sc[demand_type] = max(0.0, sc_coef.get_function_y(target_year))

        specific_consumption = SpecConsum(sc[DemandType.ELECTRICITY], sc[DemandType.HEAT], sc[DemandType.HYDROGEN])

        # efficiency scale heat as fuel todo: should this be done later? reference says no

        # convert from GWh/thousand employee to TWh/thousand employee
        specific_consumption.scale(get_conversion_scalar(Unit.GWh, Unit.TWh))

        return specific_consumption

    def get_heat_levels(self) -> Heat:
        """ Get the heat levels. """
        return self.ctrl.cts_settings.heat_levels

    def get_load_profile(self) -> dict[DemandType, [float]]:
        """ Get the load profiles. """
        return self.cts_input.load_profile

    def get_employee_share_of_population_country(self, country_name, subsector_name) -> float:
        """ Get the share of population that is employed in a certain subsector. """
        cts_pp: CtsPreprocessed = self.preprocessor.countries_pp[country_name].cts_pp

        # get target_year form settings
        target_year = self.ctrl.general_settings.target_year

        # get coef from preprocessing
        ts_employee_share: Timeseries = cts_pp.employee_share_in_subsector_country[subsector_name]
        coef = ts_employee_share.get_coef()
        coef.set_method(ForecastMethod.LINEAR)

        # predict
        value_in_2018 = ts_employee_share.get_value_at_year(2018)
        prediction = max(0.0, coef.get_function_y(target_year))  # cannot be smaller than 0
        # prediction = min(prediction, value_in_2018 * 1.15)  # cap it.
        prediction = min(prediction, 1.0)

        return prediction

    def get_employee_share_of_population_nuts2(self, country_name, subsector_name) -> dict[str, float]:
        """ Get the share of population in a nuts2 region that is employed in a certain subsector. """
        cts_pp: CtsPreprocessed = self.preprocessor.countries_pp[country_name].cts_pp

        # get target_year form settings
        target_year = self.ctrl.general_settings.target_year

        dict_res = dict[str, float]()
        for region_name, dict_subsector_employee_share in cts_pp.employee_share_in_subsector_nuts2.items():
            # get coef from preprocessing
            ts_employee_share = dict_subsector_employee_share[subsector_name]
            coef = ts_employee_share.get_coef()
            coef.set_method(ForecastMethod.LINEAR)

            # predict
            value_in_2018 = ts_employee_share.get_value_at_year(2018)
            prediction = max(0.0, coef.get_function_y(target_year))  # cannot be smaller than 0
            prediction = min(prediction, value_in_2018 * 1.15)  # cap it. todo: maybe this can be done better?
            dict_res[region_name] = prediction

        return dict_res

    def get_population_country(self, country_name) -> float:
        """ Get the population of the country in target year. """
        return self.country_if.get_population_country_in_target_year(country_name)

    def get_population_nuts2(self, country_name) -> dict[str, float]:
        """ Get the population of each nuts2 region of a country in target year. """
        return self.country_if.get_population_nuts2_in_target_year(country_name)

    def get_nuts2_spec_demand_scalar(self, country_name, subsector_name) -> dict[str, float]:
        """ Get the scalar for the specific consumption that distributes demand across nuts2 regions. """
        if self.ctrl.cts_settings.nuts2_distribution_per_pop_density:
            return self.country_if.get_population_nuts2_percentages_in_target_year(country_name)
        else:
            employee_share_nuts2 = self.get_employee_share_of_population_nuts2(country_name, subsector_name)
            population_nuts2 = self.get_population_nuts2(country_name)
            res_dict = dict[str, float]()
            for region_name, employee_share in employee_share_nuts2.items():
                res_dict[region_name] = employee_share * population_nuts2[region_name]
            return res_dict

    def get_nuts2_regions(self, country_name) -> [str]:
        """ Get the nuts2 regions for a country. """
        return self.country_if.get_population_nuts2_in_target_year(country_name).keys()  # todo: make more pretty

    def get_heat_substitution(self) -> dict[DemandType, float]:
        """ Get the heat substitution variables from settings. """
        return self.ctrl.cts_settings.heat_substitution
