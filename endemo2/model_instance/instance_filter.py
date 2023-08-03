from endemo2.general.nuts_tree import NutsRegionLeaf
from endemo2.general.demand_containers import SC, Heat, CA
from endemo2.enumerations import DemandType
from endemo2.input.control_parameters import ControlParameters
from endemo2.preprocessing.preprocessor import Preprocessor
from endemo2.sectors.sector import SectorIdentifier
from endemo2.data_analytics.prediction_models import TwoDseries, RigidTimeseries, IntervalForecast
from input.input import IndustryInput, GeneralInput


class CountryInstanceFilter:

    def __init__(self, ctrl: ControlParameters, general_input: GeneralInput, preprocessor: Preprocessor):
        self.ctrl = ctrl
        self.general_input = general_input
        self.preprocessor = preprocessor

    def get_country_abbreviations(self, country_name) -> CA:
        return self.general_input.abbreviations[country_name]

    def get_active_sectors(self) -> [SectorIdentifier]:
        return self.ctrl.general_settings.get_active_sectors()

    def get_nuts2_population_percentages(self, country_name) -> dict[str, float]:
        country_pp = self.preprocessor.countries_pp[country_name]
        historical_nuts2_population_data = country_pp.nuts2_pp.population_historical_tree_root
        prognosis_nuts2_population_data = country_pp.nuts2_pp.population_prognosis_tree_root

        target_year = self.ctrl.general_settings.target_year

        nuts2_population_in_target_year = dict[str, float]()
        country_population_in_target_year: float = 0.0

        if target_year < self.ctrl.industry_settings.last_available_year:
            # use historical data
            nuts2_leafs: [NutsRegionLeaf] = historical_nuts2_population_data.get_all_leaf_nodes()
            total_pop: float = 0.0

            for nuts2_leaf in nuts2_leafs:
                region_name = nuts2_leaf.region_name
                his_nuts2_ts: RigidTimeseries = nuts2_leaf.get()
                nuts2_population_in_target_year[region_name] = his_nuts2_ts.get_value_at_year(target_year)
                total_pop += nuts2_population_in_target_year[region_name]
        else:
            # use prediction data
            nuts2_leafs: [NutsRegionLeaf] = prognosis_nuts2_population_data.get_all_leaf_nodes()
            nuts2_forecast_start_year = self.ctrl.industry_settings.last_available_year    # TODO: maybe use other year?

            for nuts2_leaf in nuts2_leafs:
                region_name = nuts2_leaf.region_name

                # get start point for prediction data
                his_start_year_ts: RigidTimeseries  = historical_nuts2_population_data.get_specific_node(region_name).get()
                nuts2_population_in_start_year: float = his_start_year_ts.get_value_at_year(nuts2_forecast_start_year)

                # do forecast for nuts2 region
                nuts2_pop_forecast: IntervalForecast = nuts2_leaf.get()
                nuts2_population_in_target_year[region_name] = \
                    nuts2_pop_forecast.get_forecast(target_year,
                                                    (nuts2_forecast_start_year,nuts2_population_in_start_year))

                # sum up, to get country population
                country_population_in_target_year += nuts2_population_in_target_year[region_name]

        # finally fill result structure by dividing nuts2 region population though total population
        result_nuts2_population_percentage = dict[str, float]()
        for region_name, region_pop in nuts2_population_in_target_year.items():
            result_nuts2_population_percentage[region_name] = region_pop / country_population_in_target_year

        return result_nuts2_population_percentage


class IndustryInstanceFilter:

    def __init__(self, ctrl: ControlParameters, industry_input: IndustryInput, preprocessor: Preprocessor,
                 country_instance_filter: CountryInstanceFilter):
        self.rest_sector_input = industry_input.rest_sector_input
        self.ctrl = ctrl
        self.preprocessor = preprocessor
        self.country_instance_filter = country_instance_filter

    def get_nuts2_rest_sector_capacities(self, country_name) -> dict[str, float]:
        return self.country_instance_filter.get_nuts2_population_percentages(country_name)

    def get_target_year(self) -> int:
        return self.ctrl.general_settings.target_year

    def get_active_product_names(self):
        return self.ctrl.industry_settings.active_product_names

    def get_rest_calc_data(self, country_name) -> dict[DemandType, (float, float)]:
        return self.rest_sector_input.rest_calc_data[country_name]

    def get_rest_sector_growth_rate(self) -> float:
        return self.ctrl.industry_settings.rest_sector_growth_rate

    def get_rest_basis_year(self) -> int:
        return self.rest_sector_input.rest_calc_basis_year

    def get_rest_heat_levels(self) -> Heat:
        return self.rest_sector_input.rest_sector_heat_levels


class ProductInstanceFilter:
    """
    Functions as a filter between the instance settings and the model instance.
    """
    def __init__(self, ctrl: ControlParameters, preprocessor: Preprocessor):
        self.ctrl = ctrl
        self.preprocessor = preprocessor

    def get_nuts2_capacities(self, country_name, product_name) -> dict[str, float]:
        country_pp = self.preprocessor.countries_pp[country_name]
        product_pp = country_pp.industry_pp.products_pp[product_name]
        return product_pp.nuts2_pp.nuts2_installed_capacity

    def get_specific_consumption_po(self, country_name, product_name) -> SC:
        """ Get specific consumption in TWh / t"""
        country_pp = self.preprocessor.countries_pp[country_name]
        product_pp = country_pp.industry_pp.products_pp[product_name]

        gen_s = self.ctrl.general_settings

        sc_pp = product_pp.specific_consumption_pp

        if sc_pp.historical_sc_available:
            target_year = gen_s.target_year
            sc_his = sc_pp.specific_consumption_historical

            electricity = sc_his[DemandType.ELECTRICITY].get_coef().get_function_y(target_year)
            heat = sc_his[DemandType.HEAT].get_coef().get_function_y(target_year)
            hydrogen = sc_his[DemandType.HYDROGEN].get_coef().get_function_y(target_year)

            specific_consumption = SC(electricity, heat, hydrogen)
            specific_consumption.scale(1 / 3600000)     # convert from GJ/t to TWh/t, TODO: implement nicer
            return specific_consumption

        elif not sc_pp.historical_sc_available:
            default_cs = sc_pp.default_specific_consumption
            specific_consumption = SC(default_cs.electricity, default_cs.heat, default_cs.hydrogen)
            specific_consumption.scale(1 / 3600000)  # convert from GJ/t to TWh/t, TODO: as above
            return specific_consumption

    def get_perc_used(self, product_name) -> float:
        return self.ctrl.industry_settings.product_settings[product_name].perc_used

    def get_heat_levels(self, product_name) -> Heat:
        """ Get heat levels in perc/100. """
        ind_s = self.ctrl.industry_settings
        heat_levels = ind_s.product_settings[product_name].heat_levels
        return heat_levels

    def get_amount(self, country_name, product_name) -> float:
        """ Get amount in t. """
        country_pp = self.preprocessor.countries_pp[country_name]
        product_pp = country_pp.industry_pp.products_pp[product_name]

        gen_s = self.ctrl.general_settings
        ind_s = self.ctrl.industry_settings

        active_TwoDSeries: TwoDseries

        use_per_capita = ind_s.production_quantity_calc_per_capita
        use_gdp = ind_s.use_gdp_as_x

        # decide which preprocessed data to use, depending on instance settings
        if not use_per_capita and not use_gdp:
            active_TwoDSeries = product_pp.amount_per_year
        elif use_per_capita and not use_gdp:
            active_TwoDSeries = product_pp.amount_per_capita_per_year
        elif not use_per_capita and use_gdp:
            active_TwoDSeries = product_pp.amount_per_gdp
        else:   # use_per_capita and use_gdp:
            active_TwoDSeries = product_pp.amount_per_capita_per_gdp

        # get coefficients from preprocessed data
        coef_obj = active_TwoDSeries.get_coef()
        coef_obj.set_method(ind_s.forecast_method)

        # get prognosis
        target_year = gen_s.target_year

        amount_result: float

        if use_gdp:
            # if TwoDseries is per gdp, use gdp prediction to access it
            gdp_prognosis_pp = country_pp.gdp_pp.gdp_prognosis_pp
            gdp_prog = gdp_prognosis_pp.get_forecast(target_year)
            amount_result = coef_obj.get_function_y(gdp_prog)
        else:
            # TwoDseries is per time, so just use prediction per time
            amount_result = coef_obj.get_function_y(target_year)

        # scale by population if prognosis was per capita
        if use_per_capita:
            population_prog = country_pp.population_pp.population_whole_country_prognosis.get_prognosis(target_year)
            amount_result *= population_prog

        # convert kt to t
        amount_result *= 1000

        # clamp to 0
        amount_result = max(0.0, amount_result)

        return amount_result


