"""
This module contains all instance filters that relate to the industry sector of the model.
"""
import warnings

from endemo2.data_structures.containers import SpecConsum, Heat, EH
from endemo2.data_structures.enumerations import DemandType, ForecastMethod, SubsectorGroup
from endemo2.data_structures.conversions_unit import Unit, get_conversion_scalar
from endemo2.input_and_settings.control_parameters import ControlParameters
from endemo2.model_instance.instance_filter.general_instance_filter import CountryInstanceFilter, InstanceFilter
from endemo2.preprocessing.preprocessing_step_one import ProductPreprocessed, CountryPreprocessed
from endemo2.preprocessing.preprocessor import Preprocessor
from endemo2.data_structures.prediction_models import TwoDseries, Coef
from endemo2.input_and_settings.input_general import GeneralInput
from endemo2.input_and_settings.input_industry import IndustryInput


class IndustryInstanceFilter(InstanceFilter):
    """
    This instance filter serves as a filter between the instance settings and the actual calculation of the demand
        of the industry sectors.
    """

    def __init__(self, ctrl: ControlParameters, industry_input: IndustryInput, preprocessor: Preprocessor,
                 country_instance_filter: CountryInstanceFilter):
        super().__init__(ctrl, preprocessor.countries_pp)

        self.industry_input = industry_input
        self.rest_sector_input = industry_input.rest_sector_input
        self.preprocessor = preprocessor
        self.country_instance_filter = country_instance_filter

    def get_active_products_for_this_country(self, country_name) -> list[str]:
        """ Getter for the active (or produced) products of a country. """
        dict_product_input = self.industry_input.dict_product_input
        return [product_name for product_name in self.ctrl.industry_settings.active_product_names
                if country_name in dict_product_input[product_name].production.keys()]

    def get_nuts2_rest_sector_distribution(self, country_name) -> dict[str, float]:
        """ Get the capacity/100 of the rest sector for each nuts2 region in given country. """
        return self.country_instance_filter.get_population_nuts2_percentages_in_target_year(country_name)

    def get_target_year(self) -> int:
        """ Getter for the target year. """
        return self.ctrl.general_settings.target_year

    def get_active_product_names(self) -> list[str]:
        """ Getter for the names of the product that are active in calculations. """
        return self.ctrl.industry_settings.active_product_names

    def get_rest_sector_proportion_in_basis_year(self, country_name) -> dict[DemandType, (float, float)]:
        """ Getter for the input data to calculate the rest sector demand. """
        return self.rest_sector_input.rest_demand_proportion_basis_year[country_name]

    def get_rest_sector_growth_rate(self) -> float:
        """ Getter for the growth rate of a sector specified in settings. """
        return self.ctrl.industry_settings.rest_sector_growth_rate

    def get_rest_sector_basis_year(self) -> int:
        """ Getter for the year used as the start year for the exponential growth of the rest sector. """
        return self.rest_sector_input.rest_calc_basis_year

    def get_rest_sector_heat_levels(self) -> Heat:
        """ Get the heat levels of the rest sector. """
        return self.rest_sector_input.rest_sector_heat_levels

    def get_rest_sector_hourly_profile(self, country_name: str) -> dict[DemandType, [float]]:
        """ Getter for the hourly profile of each demand type for a country and a subsector. """

        # certain countries should be substituted for other countries. This is ugly. Please find another solution.
        map_to_different_country = {
            "Switzerland": "Austria",
            "Iceland": "Austria",
            "Albania": "North Macedonia",
            "Bosnia and Herzegovina": "North Macedonia"
        }
        if country_name in map_to_different_country.keys():
            country_name = map_to_different_country[country_name]
        ###

        subsector_group = SubsectorGroup.IRON_AND_STEEL

        electricity_profile = self.industry_input.dict_electricity_profiles[country_name]
        heat_profile = self.industry_input.dict_heat_profiles[subsector_group][country_name]
        hydrogen_profile = heat_profile

        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = electricity_profile
        res_dict[DemandType.HEAT] = heat_profile
        res_dict[DemandType.HYDROGEN] = hydrogen_profile

        return res_dict

    def get_nuts2_regions(self, country_name):
        """ Getter for nuts2 regions. """
        return self.get_nuts2_rest_sector_distribution(country_name).keys()


class ProductInstanceFilter(InstanceFilter):
    """
    This instance filter serves as a filter between the instance settings and the actual calculation of the demand
        of the different products.
    """
    def __init__(self, ctrl: ControlParameters, preprocessor: Preprocessor, industry_input: IndustryInput,
                 general_input: GeneralInput, country_instance_filter: CountryInstanceFilter):
        super().__init__(ctrl, preprocessor.countries_pp)

        self.industry_input = industry_input
        self.general_input = general_input
        self.preprocessor = preprocessor
        self.country_instance_filter = country_instance_filter

        # modify preprocessed product coefficients to include the product settings
        for country_name, country_pp in self.preprocessor.countries_pp.items():
            for product_name, product_pp in country_pp.industry_pp.products_pp.items():
                product_settings = self.ctrl.industry_settings.product_settings[product_name]
                exp_growth_rate_from_settings = product_settings.manual_exp_change_rate
                product_pp.amount_vs_year.get_coef().set_exp_growth_rate(exp_growth_rate_from_settings)

    def get_nuts2_capacities(self, country_name, product_name) -> dict[str, float]:
        """ Get the nuts2 capacities for a certain product in a certain country. """
        country_pp: CountryPreprocessed = self.preprocessor.countries_pp[country_name]
        if product_name in country_pp.industry_pp.products_pp:
            if self.ctrl.industry_settings.nuts2_distribution_based_on_installed_ind_capacity:
                # installed capacities active
                product_pp: ProductPreprocessed = country_pp.industry_pp.products_pp[product_name]
                return product_pp.nuts2_installed_capacity
            else:
                # instead use population percentages
                return self.country_instance_filter.get_population_nuts2_percentages_in_target_year(country_name)
        else:
            # country doesn't have product -> zero capacities
            nuts2_regions_of_country = self.general_input.population.nuts2_population[country_name].prognosis.keys()  # TODO: make more pretty, maybe a function to get nuts2 regions for a country
            res_dict_nuts2_capacities = dict[str, float]()
            for nuts2_region_name in nuts2_regions_of_country:
                res_dict_nuts2_capacities[nuts2_region_name] = 0
            return res_dict_nuts2_capacities

    def get_specific_consumption(self, country_name, product_name) -> SpecConsum:
        """ Get specific consumption in TWh/t"""
        country_pp = self.preprocessor.countries_pp[country_name]
        product_pp = country_pp.industry_pp.products_pp[product_name]

        gen_s = self.ctrl.general_settings

        sc_pp = product_pp.specific_consumption_pp

        target_year = gen_s.target_year
        fuel_efficiency = self.general_input.efficiency["Brennstoff allgemein"].heat

        if sc_pp.historical_sc_available and self.ctrl.industry_settings.trend_calc_for_spec:

            sc_his = sc_pp.specific_consumption_historical

            # set forecast method. For specific consumption it's linear for now.
            for demand_type in [DemandType.ELECTRICITY, DemandType.HEAT, DemandType.HYDROGEN]:
                sc_his[demand_type].get_coef().set_method(ForecastMethod.LINEAR)

            # forecast specific consumption
            electricity = sc_his[DemandType.ELECTRICITY].get_coef().get_function_y(target_year)
            heat = sc_his[DemandType.HEAT].get_coef().get_function_y(target_year)
            hydrogen = sc_his[DemandType.HYDROGEN].get_coef().get_function_y(target_year)

            specific_consumption = SpecConsum(electricity, heat, hydrogen)

        else:
            default_cs = sc_pp.default_specific_consumption
            specific_consumption = SpecConsum(default_cs.electricity, default_cs.heat, default_cs.hydrogen)

            # do easy manual forecast
            basis_year = self.ctrl.industry_settings.last_available_year + 1
            change_rate = self.ctrl.industry_settings.product_settings[product_name].efficiency_improvement
            forecast_scalar = (1 - change_rate)**(target_year - basis_year)
            specific_consumption.scale(forecast_scalar)   # forecast

        # efficiency scale fuel
        specific_consumption.heat = specific_consumption.heat * fuel_efficiency

        # specific consumption cannot get better than the best available technology
        specific_consumption.cap_at_bat(self.get_bat(country_name, product_name))

        specific_consumption.scale(get_conversion_scalar(Unit.GJ, Unit.TWh))  # convert from GJ/t to TWh/t
        return specific_consumption

    def get_bat(self, country_name, product_name) -> EH:
        """ Getter for BAT consumption. """
        product_input = self.industry_input.dict_product_input[product_name]
        if country_name in product_input.bat:
            return product_input.bat[country_name]
        else:
            return product_input.bat["all"]

    def get_perc_used(self, product_name) -> float:
        """
        Getter for percentage/100 used from the product amount prognosis.
        Used for the substitution of new technologies
        """
        return self.ctrl.industry_settings.product_settings[product_name].perc_used

    def get_heat_levels(self, product_name) -> Heat:
        """ Get heat levels of a product in perc/100. """
        ind_input = self.industry_input
        heat_levels = ind_input.dict_product_input[product_name].heat_levels
        return heat_levels

    def get_amount(self, country_name, product_name) -> float:
        """ Get amount of a subsector in a country's industry in t. """
        country_pp = self.preprocessor.countries_pp[country_name]
        product_pp = country_pp.industry_pp.products_pp[product_name]

        gen_s = self.ctrl.general_settings
        ind_s = self.ctrl.industry_settings

        group_manager = self.preprocessor.group_manager

        use_per_capita = ind_s.production_quantity_calc_per_capita
        use_gdp = ind_s.use_gdp_as_x

        # if country in group -> use group coefficients
        if not group_manager.is_in_separate_group(country_name, product_name):
            coef_obj = group_manager.get_coef_for_country_and_product(country_name, product_name)
            if ind_s.forecast_method is not ForecastMethod.QUADRATIC:
                warnings.warn("what happens in this case?")
        else:
            # country not in group -> calculate separately
            active_TwoDSeries: TwoDseries

            # decide which preprocessed data to use, depending on instance settings
            if not use_per_capita and not use_gdp:
                active_TwoDSeries = product_pp.amount_vs_year
            elif use_per_capita and not use_gdp:
                active_TwoDSeries = product_pp.amount_per_capita_vs_year
            elif not use_per_capita and use_gdp:
                active_TwoDSeries = product_pp.amount_vs_gdp
            else:   # use_per_capita and use_gdp:
                active_TwoDSeries = product_pp.amount_per_capita_vs_gdp

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

        # clamp to 0
        amount_result = max(0.0, amount_result)

        return amount_result

    def get_hourly_profile(self, country_name: str, product_name: str) -> dict[DemandType, [float]]:
        """ Getter for the hourly profile of each demand type for a country and a subsector. """

        # certain countries should be substituted for other countries. This is ugly. Please find another solution. todo
        map_to_different_country = {
            "Switzerland": "Austria",
            "Iceland": "Austria",
            "Albania": "North Macedonia",
            "Bosnia and Herzegovina": "North Macedonia"
        }
        if country_name in map_to_different_country.keys():
            country_name = map_to_different_country[country_name]
        ###

        subsector_group = self.industry_input.subsector_to_group_map[product_name]

        electricity_profile = self.industry_input.dict_electricity_profiles[country_name]
        heat_profile = self.industry_input.dict_heat_profiles[subsector_group][country_name]
        hydrogen_profile = heat_profile

        res_dict = dict[DemandType, [float]]()
        res_dict[DemandType.ELECTRICITY] = electricity_profile
        res_dict[DemandType.HEAT] = heat_profile
        res_dict[DemandType.HYDROGEN] = hydrogen_profile

        return res_dict

    def get_heat_substitution(self) -> dict[DemandType, Heat]:
        """ Getter for the substitution of heat with electricity and hydrogen. """
        return self.ctrl.industry_settings.heat_substitution



