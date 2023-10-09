"""
This module contains all instance filters that relate to the general part of the model.
"""

import math

from endemo2.data_structures.containers import CA, Datapoint
from endemo2.data_structures.nuts_tree import NutsRegionLeaf
from endemo2.data_structures.prediction_models import RigidTimeseries, IntervalForecast, Timeseries
from endemo2.input_and_settings.control_parameters import ControlParameters
from endemo2.data_structures.enumerations import SectorIdentifier
from endemo2.input_and_settings.input_manager import InputManager
from endemo2.preprocessing.preprocessing_step_one import NUTS2Preprocessed, GDPPreprocessed
from endemo2.preprocessing.preprocessor import Preprocessor
from endemo2.input_and_settings.input_general import GeneralInput


class InstanceFilter:
    """ 
    The parent class of all instance filters. 
    
    :ivar ControlParameters ctrl: The control parameters object.
    :ivar Preprocessor preprocessor: The preprocessor object.
    """

    def __init__(self, ctrl: ControlParameters, preprocessor: Preprocessor):
        self.ctrl = ctrl
        self.preprocessor = preprocessor
        

class CountryInstanceFilter(InstanceFilter):
    """
    This instance filter serves as a filter between the instance settings and the actual calculation of a
    country's demand.
    """

    def __init__(self, ctrl: ControlParameters, general_input: GeneralInput, preprocessor: Preprocessor):
        super().__init__(ctrl, preprocessor)

        self.general_input = general_input

    def get_country_abbreviations(self, country_name) -> CA:
        """ Getter for the countries abbreviations. """
        return self.general_input.abbreviations[country_name]

    def get_active_sectors(self) -> list[SectorIdentifier]:
        """ Getter for the active sectors. """
        return self.ctrl.general_settings.get_active_sectors()

    def get_gdp_in_target_year(self, country_name) -> float:
        """ Getter for the gdp of a country in the target year. """
        gdp_pp = self.preprocessor.countries_pp[country_name].gdp_pp
        gdp_prognosis_pp: IntervalForecast = gdp_pp.gdp_prognosis_pp
        gdp_historical_pp: Timeseries = gdp_pp.gdp_historical_pp

        target_year = self.ctrl.general_settings.target_year

        gdp_start_point = Datapoint(2020, gdp_historical_pp.get_value_at_year(2020))  # todo: create entry in settings for this value
        if target_year <= gdp_start_point[0]:
            # use historical data
            return gdp_historical_pp.get_value_at_year(target_year)
        else:
            # prognosis
            gdp_prog: float = gdp_prognosis_pp.get_forecast(self.ctrl.general_settings.target_year, gdp_start_point)
        return gdp_prog

    def get_population_country_in_target_year(self, country_name) -> float:
        """ Getter for the population of a country in the target year. """
        population_pp = self.preprocessor.countries_pp[country_name].population_pp
        his_pop_country: Timeseries = population_pp.population_historical_whole_country
        prog_pop_country: RigidTimeseries = population_pp.population_whole_country_prognosis

        target_year = self.ctrl.general_settings.target_year

        if target_year > his_pop_country.get_last_data_entry()[0]:
            return prog_pop_country.get_value_at_year(target_year)
        else:
            return his_pop_country.get_value_at_year(target_year)

    def get_population_nuts2_in_target_year(self, country_name) -> dict[str, float]:
        """ Getter for the population for all nuts2 regions of a country in target year. """
        country_pp = self.preprocessor.countries_pp[country_name]
        nuts2_pp: NUTS2Preprocessed = country_pp.nuts2_pp
        if nuts2_pp is None:
            # country doesn't have any nuts2 data
            return dict()

        historical_nuts2_population_data = country_pp.nuts2_pp.population_historical_tree_root
        prognosis_nuts2_population_data = country_pp.nuts2_pp.population_prognosis_tree_root

        target_year = self.ctrl.general_settings.target_year

        nuts2_population_in_target_year = dict[str, float]()
        if target_year < self.ctrl.industry_settings.last_available_year:
            # use historical data
            nuts2_leafs: [NutsRegionLeaf] = historical_nuts2_population_data.get_all_leaf_nodes()

            for nuts2_leaf in nuts2_leafs:
                region_name = nuts2_leaf.region_name
                his_nuts2_ts: RigidTimeseries = nuts2_leaf.get()
                nuts2_population_in_target_year[region_name] = his_nuts2_ts.get_value_at_year(target_year)
        else:
            # use prediction data
            nuts2_leafs: [NutsRegionLeaf] = prognosis_nuts2_population_data.get_all_leaf_nodes()

            for nuts2_leaf in nuts2_leafs:
                region_name = nuts2_leaf.region_name

                # get start point for prediction data -> take last available historical data
                his_start_year_ts: RigidTimeseries = \
                    historical_nuts2_population_data.get_specific_node(region_name).get()
                nuts2_last_available_population_data_point: Datapoint = \
                    his_start_year_ts.get_last_available_data_entry_or_zero()

                # do forecast for nuts2 region
                nuts2_pop_forecast: IntervalForecast = nuts2_leaf.get()
                nuts2_population_in_target_year[region_name] = \
                    nuts2_pop_forecast.get_forecast(target_year, nuts2_last_available_population_data_point)
        return nuts2_population_in_target_year

    def get_population_nuts2_percentages_in_target_year(self, country_name) -> dict[str, float]:
        """ Getter for the population density distributed into nuts2 regions of a country in the target year. """
        country_pp = self.preprocessor.countries_pp[country_name]
        nuts2_pp: NUTS2Preprocessed = country_pp.nuts2_pp
        if nuts2_pp is None:
            # country doesn't have any nuts2 data
            return dict()

        nuts2_population_in_target_year = self.get_population_nuts2_in_target_year(country_name)
        country_population_in_target_year = self.get_population_nuts2_sum(country_name)
        # fill result structure by dividing nuts2 region population though total population
        result_nuts2_population_percentage = dict[str, float]()
        for region_name, region_pop in nuts2_population_in_target_year.items():
            result_nuts2_population_percentage[region_name] = region_pop / country_population_in_target_year

        return result_nuts2_population_percentage

    def get_population_nuts2_sum(self, country_name) -> float:
        """ Getter for the sum of the nuts2 population for a country. """
        country_pp = self.preprocessor.countries_pp[country_name]
        nuts2_pp: NUTS2Preprocessed = country_pp.nuts2_pp
        if nuts2_pp is None:
            # country doesn't have any nuts2 data
            return 0.0

        nuts2_population_in_target_year = self.get_population_nuts2_in_target_year(country_name)
        nuts2_population_sum_in_target_year = \
            math.fsum([nuts2_pop for nuts2_pop in nuts2_population_in_target_year.values()])

        return nuts2_population_sum_in_target_year

