import itertools
import warnings

from endemo2.general.country_containers import NutsRegionNode, NutsRegionLeaf
from endemo2.general.demand_containers import SC, DemandType, EH, HisProg
from endemo2.utility import utility as uty
from endemo2.utility import prediction_models as pm
from endemo2.utility.prediction_models import Coef, Timeseries, RigidTimeseries
from input.input import Input, ProductInput, GeneralInput


class SpecificConsumptionPreprocessed:
    """
    The preprocessed specific consumption for a given product.

    :ivar SC default_specific_consumption: The specific consumption for a product type, that is used as default if
        there is no historical data to predict the specific consumption.
    :ivar dict[DemandType, Timeseries] specific_consumption_historical:
        The dictionary holding the timeseries for each demand type's historical demand.
    :ivar bool historical_sc_available: Indicates whether there is any historical data for the given product in the
        given country.
    :ivar EH bat: The specific consumption of the best available technology.
    """

    def __init__(self, country_name: str, product_input: ProductInput, general_input,
                 product_amount_per_year: Timeseries):

        # read bat consumption
        if country_name in product_input.bat.keys():
            self.bat = product_input.bat[country_name]
        else:
            self.bat = product_input.bat["all"]

        # read default specific consumption for product in countries industry
        if country_name in product_input.specific_consumption_default.keys():
            self.default_specific_consumption = product_input.specific_consumption_default[country_name]
        else:
            self.default_specific_consumption = product_input.specific_consumption_default["all"]

        # get efficiency
        efficiency: EH = general_input.efficiency

        # read historical specific consumption data
        self.specific_consumption_historical = dict[DemandType, Timeseries]()
        if country_name in product_input.specific_consumption_historical:
            dict_sc_his = product_input.specific_consumption_historical[country_name]
            first_year_for_data = int(list(dict_sc_his.values())[0][0][0])  # read year range from first entry
            last_year_for_data = int(list(dict_sc_his.values())[0][-1][0])

            year_zero_list = list(zip(range(first_year_for_data, last_year_for_data + 1), itertools.repeat(0)))
            electricity_demand_sum = pm.Timeseries(year_zero_list)
            heat_demand_sum = pm.Timeseries(year_zero_list)

            for energy_carrier_name, ec_his_am in dict_sc_his.items():
                ts_historical_energy_carrier_amount = Timeseries(ec_his_am)
                energy_carrier_efficiency_electricity = efficiency[energy_carrier_name].electricity
                energy_carrier_efficiency_heat = efficiency[energy_carrier_name].heat

                # multipy with efficiency of energy carrier to get demand
                energy_carrier_electricity = \
                    Timeseries.map_y(ts_historical_energy_carrier_amount,
                                     lambda x: x * energy_carrier_efficiency_electricity * 1000)  # convert TJ->GJ
                energy_carrier_heat = \
                    Timeseries.map_y(ts_historical_energy_carrier_amount,
                                     lambda x: x * energy_carrier_efficiency_heat * 1000)  # convert TJ->GJ

                # sum total demand over all energy carriers
                electricity_demand_sum.add(energy_carrier_electricity)
                heat_demand_sum.add(energy_carrier_heat)

            # divide by product amount to get per product consumption (sc)
            self.specific_consumption_historical[DemandType.ELECTRICITY] = electricity_demand_sum.divide_by(
                product_amount_per_year).scale(1 / 1000)
            self.specific_consumption_historical[DemandType.HEAT] = heat_demand_sum.divide_by(
                product_amount_per_year).scale(1 / 1000)

            if electricity_demand_sum.is_zero() and heat_demand_sum.is_zero():
                self.historical_sc_available = False
            else:
                self.historical_sc_available = True
                # generate coefficients
                self.specific_consumption_historical[DemandType.ELECTRICITY].generate_coef()
                self.specific_consumption_historical[DemandType.HEAT].generate_coef()
        else:
            self.historical_sc_available = False


class ProductPreprocessed:
    """
    The preprocessed product information for a given country.

    :ivar Timeseries amount_per_year: Used to predict the product amount. The x-axis is time in years.
    :ivar pm.TwoDseries amount_per_gdp: Used to predict the product amount. The x-axis is the countries' gdp.
    :ivar Timeseries amount_per_capita_per_year: Used to predict the product amount per capita.
        The x-axis is time in years.
    :ivar pm.TwoDseries amount_per_capita_per_gdp: Used to predict the product amount per capita.
        The x-axis is time in years.

    :ivar SpecificConsumptionPreprocessed specific_consumption_pp: The preprocessed specific consumption data.

    :ivar Heat _heat_levels: The heat levels, that splits the forecasted heat demand into demand at different heat
        levels, by using fixed percentages.
    :ivar float _perc_used: The percentage of the predicted amount used of this product. Can be configured to model new
        technology replacing old ones.
    """
    def __init__(self, country_name: str, product_input: ProductInput, population_historical: pm.Timeseries,
                 gdp_historical: pm.Timeseries, general_input: GeneralInput):
        # read from input to transfer to model later
        self.heat_levels = product_input.heat_levels
        self.perc_used = product_input.perc_used

        # fill Timeseries and TwoDseries
        self.amount_per_year = pm.Timeseries(product_input.production[country_name])
        self.amount_per_capita_per_year = \
            pm.Timeseries.map_two_timeseries(self.amount_per_year, population_historical,
                                             lambda x, y1, y2: (x, y1 / y2))
        self.amount_per_gdp = pm.Timeseries.merge_two_timeseries(gdp_historical, self.amount_per_year)
        self.amount_per_capita_per_gdp = \
            pm.Timeseries.merge_two_timeseries(gdp_historical, self.amount_per_capita_per_year)

        # calculate coefficients
        self.amount_per_year.get_coef()
        self.amount_per_gdp.get_coef()
        self.amount_per_capita_per_year.get_coef()
        self.amount_per_capita_per_gdp.get_coef()

        # preprocess specific consumption
        self.specific_consumption_pp = \
            SpecificConsumptionPreprocessed(country_name, product_input, general_input, self.amount_per_year)


class IndustryPreprocessed:
    """
    The preprocessed industry sector for a given country.

    :ivar dict[str, ProductPreprocessed] products_pp: All preprocessed products, accessible by product name.
    """
    def __init__(self, country_name, input_manager: Input, pop_his: Timeseries, gdp_his: Timeseries):
        self.products_pp = dict()
        general_input = input_manager.general_input

        for product_name, product_input in input_manager.industry_input.active_products.items():
            if country_name in product_input.production.keys() \
                    and not uty.is_tuple_list_zero(product_input.production[country_name]):
                self.products_pp[product_name] = \
                    ProductPreprocessed(country_name, product_input, pop_his, gdp_his, general_input)


class NUTS2Preprocessed:
    """
    All preprocessed data relating to nuts2.

    :ivar dict[str, float] _nuts2_installed_capacity:
        The installed capacity for this product in each NUTS2 region for the country this product belongs to.
    :ivar NutsRegionNode population_historical_tree_root: The nuts2 tree containing all historical population data for
        a given country.
    :ivar NutsRegionNode population_prognosis_tree_root: The nuts2 tree containing all population prognosis data for a
        given country.
    """

    def __init__(self, country_name, abbreviations, nuts2_population_data: HisProg, product_input):
        self.nuts2_installed_capacity = product_input.nuts2_installed_capacity[country_name]
        self.population_historical_tree_root = NutsRegionNode(abbreviations.alpha2)
        self.population_prognosis_tree_root = NutsRegionNode(abbreviations.alpha2)

        # fill nuts historical tree
        for region_name, region_data in nuts2_population_data.historical.items():
            if len(region_name) != 4:
                continue
            # create and add leaf to root
            region_data_ts = pm.Timeseries(region_data)
            subregion = NutsRegionLeaf(region_name, region_data_ts)
            self.population_historical_tree_root.add_leaf_region(subregion)

        # fill nuts prediction tree
        for region_name, region_forecast in nuts2_population_data.prognosis.items():
            if len(region_name) != 4:
                continue
            # create and add leaf to root
            region_data_if = pm.IntervalForecast(region_forecast)
            subregion = NutsRegionLeaf(region_name, region_data_if)
            self.population_historical_tree_root.add_leaf_region(subregion)


class PopulationPreprocessed:
    """
    The preprocessed population data for a whole country.

    :ivar Timeseries population_historical_whole_country: The timeseries for the countries population.
    :ivar RigidTimeseries population_whole_country_prognosis: The manual prediction data for the countries population.
    """

    def __init__(self, country_name, general_input):
        # fill whole country population data and prognosis
        whole_country_input = general_input.population.country_population[country_name]
        self.population_historical_whole_country = pm.Timeseries(whole_country_input.historical)
        self.population_whole_country_prognosis = RigidTimeseries(whole_country_input.prognosis)


class GDPPreprocessed:
    """
    The preprocessed GDP data for a give country.

    :ivar Timeseries gdp_historical_pp: The timeseries for the historical gdp data.
    :ivar IntervalForecast gdp_prognosis_pp: The gdp's forecast.
    """
    def __init__(self, country_name, general_input: GeneralInput):
        self.gdp_historical_pp = pm.Timeseries(general_input.gdp[country_name].historical)
        self.gdp_prognosis_pp = pm.IntervalForecast(general_input.gdp[country_name].prognosis)


class CountryPreprocessed:
    """
    A preprocessed country.

    :ivar PopulationPreprocessed population_pp: The preprocessed country-wide population.
    :ivar GDPPreprocessed gdp_pp: The preprocessed gdp data.
    :ivar bool has_nuts2: Indicates whether country has data for nuts2 regions.
    :ivar NUTS2Preprocessed nuts2_pp: The preprocessed nuts2 data.
    :ivar IndustryPreprocessed industry_pp: The preprocessed industry data.
    """

    def __init__(self, country_name, input_manager: Input):
        general_input = input_manager.general_input
        abbreviations = general_input.abbreviations[country_name]

        # preprocess general country attributes
        self.population_pp = PopulationPreprocessed(country_name, general_input)
        self.gdp_pp = GDPPreprocessed(country_name, general_input)

        # preprocess NUTS2 data if present
        nuts2_data = general_input.population.nuts2_population[country_name]
        self.has_nuts2 = abbreviations.alpha2 in nuts2_data.prognosis.keys()
        if self.has_nuts2:
            self.nuts2_pp = NUTS2Preprocessed(abbreviations, nuts2_data)
        else:
            self.nuts2_pp = None

        # preprocess all active sectors (add other sectors here later)
        self.industry_pp = IndustryPreprocessed(country_name, input_manager,
                                                self.population_pp.population_historical_whole_country,
                                                self.gdp_pp.gdp_historical_pp)
