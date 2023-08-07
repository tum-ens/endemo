"""
This module contains all instance filters that relate to the industry sector of the model.
"""

from endemo2.data_structures.containers import SC, Heat
from endemo2.data_structures.enumerations import DemandType, ForecastMethod
from endemo2.input_and_settings.control_parameters import ControlParameters
from endemo2.model_instance.instance_filter.general_instance_filter import CountryInstanceFilter
from endemo2.preprocessing.preprocessing_step_one import ProductPreprocessed, CountryPreprocessed
from endemo2.preprocessing.preprocessor import Preprocessor
from endemo2.data_structures.prediction_models import TwoDseries
from input.input import IndustryInput, GeneralInput


class IndustryInstanceFilter:
    """
    This instance filter serves as a filter between the instance settings and the actual calculation of the demand
        of the industry sectors.
    """

    def __init__(self, ctrl: ControlParameters, industry_input: IndustryInput, preprocessor: Preprocessor,
                 country_instance_filter: CountryInstanceFilter):
        self.rest_sector_input = industry_input.rest_sector_input
        self.ctrl = ctrl
        self.preprocessor = preprocessor
        self.country_instance_filter = country_instance_filter
        self.industry_input = industry_input

    def get_active_products_for_this_country(self, country_name) -> list[str]:
        """ Getter for the active (or produced) products of a country. """
        dict_product_input = self.industry_input.active_products
        return [product_name for product_name in self.ctrl.industry_settings.active_product_names
                if country_name in dict_product_input[product_name].production.keys()]

    def get_nuts2_rest_sector_capacities(self, country_name) -> dict[str, float]:
        """ Get the capacity/100 of the rest sector for each nuts2 region in given country. """
        return self.country_instance_filter.get_nuts2_population_percentages_in_target_year(country_name)

    def get_target_year(self) -> int:
        """ Getter for the target year. """
        return self.ctrl.general_settings.target_year

    def get_active_product_names(self) -> list[str]:
        """ Getter for the names of the product that are active in calculations. """
        return self.ctrl.industry_settings.active_product_names

    def get_rest_calc_data(self, country_name) -> dict[DemandType, (float, float)]:
        """ Getter for the input data to calculate the rest sector demand. """
        return self.rest_sector_input.rest_calc_data[country_name]

    def get_rest_sector_growth_rate(self) -> float:
        """ Getter for the growth rate of a sector specified in settings. """
        return self.ctrl.industry_settings.rest_sector_growth_rate

    def get_rest_basis_year(self) -> int:
        """ Getter for the year used as the start year for the exponential growth of the rest sector. """
        return self.rest_sector_input.rest_calc_basis_year

    def get_rest_heat_levels(self) -> Heat:
        """ Get the heat levels of the rest sector. """
        return self.rest_sector_input.rest_sector_heat_levels


class ProductInstanceFilter:
    """
    This instance filter serves as a filter between the instance settings and the actual calculation of the demand
        of the different products.
    """
    def __init__(self, ctrl: ControlParameters, preprocessor: Preprocessor, industry_input: IndustryInput,
                 general_input: GeneralInput, country_instance_filter: CountryInstanceFilter):
        self.ctrl = ctrl
        self.preprocessor = preprocessor
        self.industry_input = industry_input
        self.general_input = general_input
        self.country_instance_filter = country_instance_filter

        # modify preprocessed product coefficients to include the product settings
        for country_name, country_pp in self.preprocessor.countries_pp.items():
            for product_name, product_pp  in country_pp.industry_pp.products_pp.items():
                product_settings = self.ctrl.industry_settings.product_settings[product_name]
                exp_growth_rate_from_settings = product_settings.manual_exp_change_rate
                product_pp.amount_per_year.get_coef().set_exp_growth_rate(exp_growth_rate_from_settings)

    def get_nuts2_capacities(self, country_name, product_name) -> dict[str, float]:
        """ Get the nuts2 capacities for a certain product in a certain country. """
        country_pp: CountryPreprocessed = self.preprocessor.countries_pp[country_name]
        if product_name in country_pp.industry_pp.products_pp:
            product_pp: ProductPreprocessed = country_pp.industry_pp.products_pp[product_name]
            return product_pp.nuts2_installed_capacity
        else:
            # country doesn't have product -> zero capacities
            nuts2_regions_of_country = self.general_input.population.nuts2_population[country_name].prognosis.keys()  # TODO: make more pretty, maybe a function to get nuts2 regions for a country
            res_dict_nuts2_capacities = dict[str, float]()
            for nuts2_region_name in nuts2_regions_of_country:
                res_dict_nuts2_capacities[nuts2_region_name] = 0
            return res_dict_nuts2_capacities

    def get_specific_consumption_po(self, country_name, product_name) -> SC:
        """ Get specific consumption in TWh/t"""
        country_pp = self.preprocessor.countries_pp[country_name]
        product_pp = country_pp.industry_pp.products_pp[product_name]

        gen_s = self.ctrl.general_settings

        sc_pp = product_pp.specific_consumption_pp

        if sc_pp.historical_sc_available:
            target_year = gen_s.target_year
            sc_his = sc_pp.specific_consumption_historical

            # set forecast method. For specific consumption it's linear for now.
            for demand_type in [DemandType.ELECTRICITY, DemandType.HEAT, DemandType.HYDROGEN]:
                sc_his[demand_type].get_coef().set_method(ForecastMethod.LINEAR)
            # forecast specific consumption
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
        """
        Getter for percentage/100 used from the product amount prognosis.
        Used for the substitution of new technologies
        """
        return self.ctrl.industry_settings.product_settings[product_name].perc_used

    def get_heat_levels(self, product_name) -> Heat:
        """ Get heat levels of a product in perc/100. """
        ind_input = self.industry_input
        heat_levels = ind_input.active_products[product_name].heat_levels
        return heat_levels

    def get_amount(self, country_name, product_name) -> float:
        """ Get amount of a product in a country's industry in t. """
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
            gdp_prog: float = self.country_instance_filter.get_gdp_in_target_year(country_name)
            amount_result = coef_obj.get_function_y(gdp_prog)
        else:
            # TwoDseries is per time, so just use prediction per time
            amount_result = coef_obj.get_function_y(target_year)

        # scale by population if prognosis was per capita
        if use_per_capita:
            population_prog = country_pp.population_pp.population_whole_country_prognosis.get_value_at_year(target_year)
            amount_result *= population_prog

        # convert kt to t
        amount_result *= 1000

        # clamp to 0
        amount_result = max(0.0, amount_result)

        return amount_result


