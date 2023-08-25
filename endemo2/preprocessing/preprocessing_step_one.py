"""
This module contains all classed used for the first stage of preprocessing.
"""
from __future__ import annotations

from endemo2.data_structures.nuts_tree import NutsRegionNode, NutsRegionLeaf
from endemo2.data_structures.containers import EH, HisProg
from endemo2.data_structures.enumerations import DemandType, SectorIdentifier, TransportModal, TrafficType
from endemo2.data_structures.prediction_models import Timeseries, RigidTimeseries, IntervalForecast
from endemo2.input_and_settings.input_general import GeneralInput, Abbreviations
from endemo2.input_and_settings.input_households import HouseholdsInput, HouseholdsSubsectorId
from endemo2.input_and_settings.input_manager import InputManager
from endemo2.input_and_settings.input_cts import CtsInput
from endemo2.input_and_settings.input_industry import ProductInput
from endemo2.input_and_settings.input_transport import TransportInput
from endemo2.preprocessing.preprocessing_utility import energy_carrier_to_energy_consumption

class TransportPreprocessed:
    """
    Preprocesses everything of the transport sector.

    :ivar dict[TrafficType, dict[TransportModal, Timeseries]] modal_split_timeseries: The preprocessed
        percentages of modal splits for each traffic type.
    """
    def __init__(self, country_name: str, general_input: GeneralInput, transport_input: TransportInput):

        self.modal_split_timeseries = dict[TrafficType, dict[TransportModal, Timeseries]]()
        for traffic_type in TransportInput.tra_modal_lists.keys():
            # preprocess modal split timeseries for given traffic type
            self.modal_split_timeseries[traffic_type] = dict[TransportModal, Timeseries]()  # {modal_id -> ts}
            for modal_id, data in transport_input.modal_split_his[traffic_type][country_name].items():
                ts = Timeseries(data)
                # preprocess coefficients
                ts.generate_coef()
                # save
                self.modal_split_timeseries[traffic_type][modal_id] = ts


class HouseholdsPreprocessed:
    """
    Preprocesses everything of the households sector.

    :ivar dict[HouseholdsSubsectorId, dict[DemandType, Timeseries]] sectors_pp: The timeseries for the energy
        consumption of each subsector and demand type.
    """
    def __init__(self, country_name: str, general_input: GeneralInput, households_input: HouseholdsInput,
                 population_historical: Timeseries):

        # create timeseries out of historical energy carrier data
        dict_subsector_energy_carrier_his = households_input.historical_consumption[country_name]
        efficiency_hh = general_input.efficiency_hh

        # enum_subsector -> str_energy_carrier -> [(float, float)]
        self.sectors_pp = dict[HouseholdsSubsectorId, dict[DemandType, Timeseries]]()
        for subsector, dict_energy_carrier_his in dict_subsector_energy_carrier_his.items():

            ts_electricity, ts_heat = energy_carrier_to_energy_consumption(efficiency_hh, dict_energy_carrier_his)

            # divide by historical population to make the time trend per capita
            self.sectors_pp[subsector] = dict[DemandType, Timeseries]()
            self.sectors_pp[subsector][DemandType.ELECTRICITY] = ts_electricity.divide_by(population_historical)
            self.sectors_pp[subsector][DemandType.HEAT] = ts_heat.divide_by(population_historical)
            self.sectors_pp[subsector][DemandType.HYDROGEN] = Timeseries([(2018, 0.0)])

            # generate coefficients
            for demand_type in [DemandType.ELECTRICITY, DemandType.HEAT, DemandType.HYDROGEN]:
                self.sectors_pp[subsector][demand_type].generate_coef()


class CtsPreprocessed:
    """
    Preprocesses everything of the cts sector.

    :ivar dict[DemandType, Timeseries] specific_consumption: The specific consumption timeseries for each demand type
        of form {demand_type -> timeseries}.
    :ivar dict[str, Timeseries] employee_share_in_subsector_country: The timeseries of the share of the population that
        is an employee in a certain subsector. Is of form {country_name -> timeseries}
    :ivar dict[str, dict[str, Timeseries]] employee_share_in_subsector_nuts2: The timeseries of the share of the
        population of a nuts2 region that is an employee in a certain subsector.
        Is of form {country_name -> {region_name -> timeseries}}
    """

    def __init__(self, country_name: str, general_input: GeneralInput, cts_input: CtsInput, pop_his: Timeseries,
                 pop_nuts2_his: NutsRegionNode):

        # preprocess specific consumption; demand_type -> timeseries
        self.specific_consumption = \
            CtsPreprocessed.preprocess_specific_consumption(country_name, general_input, cts_input)

        # preprocess subsector number of employees per country; subsector_name -> num_employees_timeseries
        self.employee_share_in_subsector_country = dict[str, Timeseries]()
        for subsector_name, num_employees_data in cts_input.dict_employee_number_country[country_name].items():
            # put data into timeseries object
            ts_num_employees = Timeseries(num_employees_data)

            # calculate share of population
            ts_num_employees.divide_by(pop_his)

            # generate coefficients
            ts_num_employees.generate_coef()

            # save
            self.employee_share_in_subsector_country[subsector_name] = ts_num_employees

        # preprocess subsector number of employees per nuts2; nuts2_region -> subsector_name -> num_employees_timeseries
        self.employee_share_in_subsector_nuts2 = dict[str, dict[str, Timeseries]]()
        for region_name, dict_subsector_employee in cts_input.dict_employee_number_nuts2[country_name].items():
            dict_nuts2_pop_his = dict([(leaf.region_name, leaf.data) for leaf in pop_nuts2_his.get_all_leaf_nodes()])
            for subsector_name, num_employees_data in dict_subsector_employee.items():
                # put data into timeseries object
                ts_num_employees = Timeseries(num_employees_data)

                # calculate share of population
                ts_num_employees.divide_by(dict_nuts2_pop_his[region_name])

                # generate coefficients
                ts_num_employees.generate_coef()

                # save
                if region_name not in self.employee_share_in_subsector_nuts2.keys():
                    self.employee_share_in_subsector_nuts2[region_name] = dict()
                self.employee_share_in_subsector_nuts2[region_name][subsector_name] = ts_num_employees

    @classmethod
    def preprocess_specific_consumption(cls, country_name: str, general_input: GeneralInput, cts_input: CtsInput) \
            -> dict[DemandType, Timeseries]:
        """
        Preprocesses the specific consumption of the cts sector.

        :param country_name: The name of the country to preprocess the specific consumption for
        :param general_input: The general input object.
        :param cts_input: The cts sector input object.
        :return: The specific consumption timeseries for each demand type of form {demand_type -> timeseries}.
        """
        # get data from input
        dict_ec_his: dict[str, [(float, float)]] = cts_input.energy_carrier_consumption[country_name]
        efficiency = general_input.efficiency

        # calculate demand from energy carriers with efficiency
        electricity_demand_sum, heat_demand_sum = energy_carrier_to_energy_consumption(efficiency, dict_ec_his)

        # get number of employees per year in cts sector historical
        number_of_employees_ts = Timeseries(cts_input.dict_employee_number_country_cts[country_name])

        # divide by number of employees to get specific consumption
        res_specific_consumption = dict[DemandType, Timeseries]()  # demand_type -> Timeseries
        res_specific_consumption[DemandType.ELECTRICITY] = electricity_demand_sum.divide_by(number_of_employees_ts)
        res_specific_consumption[DemandType.HEAT] = heat_demand_sum.divide_by(number_of_employees_ts)
        res_specific_consumption[DemandType.HYDROGEN] = Timeseries([(2018, 0.0)])

        # generate coefficients
        for demand_type in [DemandType.ELECTRICITY, DemandType.HEAT, DemandType.HYDROGEN]:
            res_specific_consumption[demand_type].generate_coef()

        return res_specific_consumption


class SpecificConsumptionPreprocessed:
    """
    The preprocessed specific consumption for a given product.

    :ivar SpecConsum default_specific_consumption: The specific consumption for a product type, that is used as default
        if there is no historical data to predict the specific consumption.
    :ivar dict[DemandType, Timeseries] specific_consumption_historical:
        The dictionary holding the timeseries for each demand type's historical demand.
    :ivar bool historical_sc_available: Indicates whether there is any historical data for the given product in the
        given country.
    :ivar EH bat: The specific consumption of the best available technology.
    """

    def __init__(self, country_name: str, product_input: ProductInput, general_input: GeneralInput,
                 quantity_per_year: Timeseries):

        # read bat consumption
        if country_name in product_input.bat.keys():
            self.bat = product_input.bat[country_name]
        else:
            self.bat = product_input.bat["all"]

        # read default specific consumption for product in countries_in_group industry
        if country_name in product_input.specific_consumption_default.keys():
            self.default_specific_consumption = product_input.specific_consumption_default[country_name]
        else:
            self.default_specific_consumption = product_input.specific_consumption_default["all"]

        # get efficiency
        efficiency: dict[str, EH] = general_input.efficiency

        # read historical specific consumption data
        self.specific_consumption_historical = dict[DemandType, Timeseries]()
        if product_input.specific_consumption_historical is not None \
                and country_name in product_input.specific_consumption_historical:
            dict_sc_his = product_input.specific_consumption_historical[country_name]

            electricity_demand_sum, heat_demand_sum = energy_carrier_to_energy_consumption(efficiency, dict_sc_his)

            # divide by product amount to get per product consumption (sc)
            self.specific_consumption_historical[DemandType.ELECTRICITY] = electricity_demand_sum.divide_by(
                quantity_per_year).scale(1 / 1000).scale(1000)  # kt -> t; TJ/t -> GJ/t
            self.specific_consumption_historical[DemandType.HEAT] = heat_demand_sum.divide_by(
                quantity_per_year).scale(1 / 1000).scale(1000)  # kt -> t; TJ/t -> GJ/t

            if electricity_demand_sum.is_zero() and heat_demand_sum.is_zero():
                self.historical_sc_available = False
            else:
                self.historical_sc_available = True
                # generate coefficients
                self.specific_consumption_historical[DemandType.ELECTRICITY].generate_coef()
                self.specific_consumption_historical[DemandType.HEAT].generate_coef()

                # create hydrogen dummy. If there is any data for hydrogen, replace this
                self.specific_consumption_historical[DemandType.HYDROGEN] = Timeseries([(2018, 0.0)])
                self.specific_consumption_historical[DemandType.HYDROGEN].generate_coef()
        else:
            self.historical_sc_available = False


class ProductPreprocessed:
    """
    The preprocessed product information for a given country.

    :ivar Timeseries amount_vs_year: Used to predict the product amount. The x-axis is time in years.
    :ivar TwoDseries amount_vs_gdp: Used to predict the product amount. The x-axis is the countries_in_group' gdp.
    :ivar Timeseries amount_per_capita_vs_year: Used to predict the product amount per capita.
        The x-axis is time in years.
    :ivar TwoDseries amount_per_capita_vs_gdp: Used to predict the product amount per capita.
        The x-axis is time in years.

    :ivar SpecificConsumptionPreprocessed specific_consumption_pp: The preprocessed specific consumption data.
    :ivar dict[str, float] _nuts2_installed_capacity:
        The installed capacity for this product in each NUTS2 region for the country this product belongs to.

    """

    def __init__(self, country_name: str, product_input: ProductInput, population_historical: Timeseries,
                 gdp_historical: Timeseries, general_input: GeneralInput):
        if country_name in product_input.production.keys():
            # fill Timeseries and TwoDseries
            self.amount_vs_year = Timeseries(product_input.production[country_name])
        else:
            # if country not in product tables, we know it doesn't product anything. Take any reasonable year to put 0.
            self.amount_vs_year = Timeseries([(2000, 0.0)])

        self.amount_per_capita_vs_year = \
            Timeseries.map_two_timeseries(self.amount_vs_year, population_historical,
                                          lambda x, y1, y2: (x, y1 / y2))
        self.amount_vs_gdp = Timeseries.merge_two_timeseries(gdp_historical, self.amount_vs_year)
        self.amount_per_capita_vs_gdp = \
            Timeseries.merge_two_timeseries(gdp_historical, self.amount_per_capita_vs_year)

        # calculate coefficients
        self.amount_vs_year.generate_coef()
        self.amount_vs_gdp.generate_coef()
        self.amount_per_capita_vs_year.generate_coef()
        self.amount_per_capita_vs_gdp.generate_coef()

        # preprocess specific consumption
        self.specific_consumption_pp = \
            SpecificConsumptionPreprocessed(country_name, product_input, general_input, self.amount_vs_year)

        # save nuts2 installed capacity
        self.nuts2_installed_capacity = product_input.nuts2_installed_capacity[country_name]


class IndustryPreprocessed:
    """
    The preprocessed industry sector for a given country.

    :ivar dict[str, ProductPreprocessed] products_pp: All preprocessed products, accessible by product name.
    """

    def __init__(self, country_name, input_manager: InputManager, pop_his: Timeseries, gdp_his: Timeseries):
        self.products_pp = dict()
        general_input = input_manager.general_input

        for product_name, product_input in input_manager.industry_input.dict_product_input.items():
            self.products_pp[product_name] = \
                ProductPreprocessed(country_name, product_input, pop_his, gdp_his, general_input)


class NUTS2Preprocessed:
    """
    All preprocessed data relating to nuts2 that are general. (For product-specific nuts2 data, see ProductPreprocessed)

    :ivar NutsRegionNode population_historical_tree_root: The nuts2 tree containing all historical population data for
        a given country.
    :ivar NutsRegionNode population_prognosis_tree_root: The nuts2 tree containing all population prognosis data for a
        given country.
    """

    def __init__(self, country_name, nuts2_population_data: HisProg):
        abbrev = Abbreviations.dict_en_alpha2_map[country_name]
        self.population_historical_tree_root = NutsRegionNode(abbrev)
        self.population_prognosis_tree_root = NutsRegionNode(abbrev)

        # fill nuts historical tree
        for region_name, region_data in nuts2_population_data.historical.items():
            if len(region_name) != 4:
                continue
            # create and add leaf to root
            region_data_ts = Timeseries(region_data)
            subregion = NutsRegionLeaf(region_name, region_data_ts)
            self.population_historical_tree_root.add_leaf_region(subregion)

        # fill nuts prediction tree
        for region_name, region_forecast in nuts2_population_data.prognosis.items():
            if len(region_name) != 4:
                continue
            # create and add leaf to root
            region_data_if = IntervalForecast(region_forecast)
            subregion = NutsRegionLeaf(region_name, region_data_if)
            self.population_prognosis_tree_root.add_leaf_region(subregion)


class PopulationPreprocessed:
    """
    The preprocessed population data for a whole country.

    :ivar Timeseries population_historical_whole_country: The timeseries for the countries_in_group population.
    :ivar RigidTimeseries population_whole_country_prognosis: The manual prediction data for the countries_in_group
        population.
    """

    def __init__(self, country_name, general_input):
        # fill whole country population data and prognosis
        whole_country_input = general_input.population.country_population[country_name]
        self.population_historical_whole_country = Timeseries(whole_country_input.historical)
        self.population_whole_country_prognosis = RigidTimeseries(whole_country_input.prognosis)


class GDPPreprocessed:
    """
    The preprocessed GDP data for a give country.

    :ivar Timeseries gdp_historical_pp: The timeseries for the historical gdp data.
    :ivar IntervalForecast gdp_prognosis_pp: The gdp's forecast.
    """

    def __init__(self, country_name, general_input: GeneralInput):
        self.gdp_historical_pp = Timeseries(general_input.gdp[country_name].historical)
        self.gdp_prognosis_pp = IntervalForecast(general_input.gdp[country_name].prognosis)


class CountryPreprocessed:
    """
    A preprocessed country.

    :ivar PopulationPreprocessed population_pp: The preprocessed country-wide population.
    :ivar GDPPreprocessed gdp_pp: The preprocessed gdp data.
    :ivar bool has_nuts2: Indicates whether country has data for nuts2 regions.
    :ivar NUTS2Preprocessed nuts2_pp: The preprocessed nuts2 data.
    :ivar IndustryPreprocessed industry_pp: The preprocessed industry data.
    """

    def __init__(self, country_name, input_manager: InputManager):
        general_input = input_manager.general_input

        # preprocess general country attributes
        self.population_pp = PopulationPreprocessed(country_name, general_input)
        self.gdp_pp = GDPPreprocessed(country_name, general_input)

        # preprocess NUTS2 data if present
        self.has_nuts2 = country_name in general_input.population.nuts2_population  # TODO: also make more pretty
        if self.has_nuts2:
            nuts2_data = general_input.population.nuts2_population[country_name]
            self.nuts2_pp = NUTS2Preprocessed(country_name, nuts2_data)
        else:
            self.nuts2_pp = None

        # preprocess all active sectors
        active_sectors = input_manager.ctrl.general_settings.get_active_sectors()
        if SectorIdentifier.INDUSTRY in active_sectors:
            self.industry_pp = IndustryPreprocessed(country_name, input_manager,
                                                    self.population_pp.population_historical_whole_country,
                                                    self.gdp_pp.gdp_historical_pp)
        if SectorIdentifier.COMMERCIAL_TRADE_SERVICES in active_sectors:
            self.cts_pp = CtsPreprocessed(country_name, input_manager.general_input, input_manager.cts_input,
                                          self.population_pp.population_historical_whole_country,
                                          self.nuts2_pp.population_historical_tree_root)
        if SectorIdentifier.HOUSEHOLDS in active_sectors:
            self.households_pp = HouseholdsPreprocessed(country_name, input_manager.general_input,
                                                        input_manager.hh_input,
                                                        self.population_pp.population_historical_whole_country)
        if SectorIdentifier.TRANSPORT in active_sectors:
            self.transport_pp = TransportPreprocessed(country_name, general_input, input_manager.transport_input)
