from __future__ import annotations

import enum
import warnings

from endemo2.input import input
from endemo2.sectors import industry_sector, sector
from endemo2.utility import prediction_models as pm
from endemo2.general.country_containers import Population, NutsRegion
from endemo2.general import demand_containers as dc


class Country:
    """
    The Country connects all sectors and data from a single country. It is a completely self-contained unit.

    :param name: Name of the country.
    :param input_manager:
        The input manager containing all the input files, so country can fill the variables in its constructor.

    :ivar str _name: The name of the country (en).
    :ivar [str] _abbreviations: Possible abbreviations for this country.
    :ivar Population[PredictedTimeseries, NutsRegion] _population: Population object, containing important data and
        timeseries of the countries' population.
    :ivar TimeStepSequence _gdp: The Timeseries for the GDP of this country.
    :ivar dict[SectorIdentifier, Sector] _sectors: The sector objects for this country, accessible by the sector
        identifier.
    """

    def __init__(self, name: str, input_manager: input.Input):

        self._name = name
        self._sectors = dict()

        # fill abbreviations
        self._abbreviations = input_manager.general_input.abbreviations[self._name]

        # create population timeseries
        country_population = \
            pm.PredictedTimeseries(
                historical_data=input_manager.general_input.population.country_population[self._name].historical,
                prediction_data=input_manager.general_input.population.country_population[self._name].prognosis)

        # create nuts2 tree
        nuts2_data = input_manager.general_input.population.nuts2_population[self._name]
        nuts2_root: NutsRegion
        if self._abbreviations.alpha2 in nuts2_data.prognosis.keys():
            nuts2_root = NutsRegion(self._abbreviations.alpha2, nuts2_data.historical[self._abbreviations.alpha2],
                                    nuts2_data.prognosis[self._abbreviations.alpha2])
        else:
            nuts2_root = NutsRegion(self._abbreviations.alpha2)

        for region_name, region_data in nuts2_data.historical.items():
            if region_name == self._abbreviations.alpha2:
                continue
            # create and add subregion to root
            subregion: NutsRegion
            if region_name in nuts2_data.prognosis.keys():
                subregion = NutsRegion(region_name, historical_data=region_data,
                                       prediction_data=nuts2_data.prognosis[region_name])
            else:
                subregion = NutsRegion(region_name, historical_data=region_data)
            nuts2_root.add_child_region(subregion)

        # fill population member variable
        self._population = \
            Population(country_population, nuts2_root,
                       input_manager.ctrl.industry_settings.nuts2_distribution_based_on_installed_ind_capacity)

        # create gdp timeseries
        self._gdp = pm.TimeStepSequence(
            historical_data=input_manager.general_input.gdp[self._name].historical,
            progression_data=input_manager.general_input.gdp[self._name].prognosis)

        # create sectors and pass on required data
        active_sectors = input_manager.ctrl.general_settings.get_active_sectors()

        if "industry" in active_sectors:
            self._sectors[sector.SectorIdentifier.INDUSTRY] = \
                industry_sector.Industry(self._name, self._population, self._gdp, input_manager)

        # create warnings
        if not self._abbreviations:
            warnings.warn("Country " + self._name + " has an empty list of Abbreviations.")
        if not self._population.country_level_population.get_data():
            warnings.warn("Country " + self._name + " has an empty list of historical Population.")
        if not self._population.country_level_population.get_prediction_raw():
            warnings.warn("Country " + self._name + " has an empty list of prediction for Population.")
        if not self._gdp.get_historical_data_raw():
            warnings.warn("Country " + self._name + " has an empty list of historical gdp.")
        if not self._gdp.get_interval_change_rate_raw():
            warnings.warn("Country " + self._name + " has an empty list of interval_changeRate for gdp.")

    def calculate_total_demand(self, year: int) -> dc.Demand:
        """
        Sum the demand over all sectors of the country.

        :param year: Target year for which the prediction should be calculated.
        :return: The demand for a country summed over all sectors.
        """
        total_demand = dc.Demand()

        for sector_name, obj_sector in self._sectors.items():
            total_demand.add(obj_sector.calculate_forecasted_demand(year))

        return total_demand

    def get_name(self) -> str:
        """
        Getter for the country name.

        :return: The country name (en).
        """
        return self._name

    def get_population(self) -> Population:
        """
        Getter for the population container object.

        :return: The countries' population container object.
        """
        return self._population

    def get_gdp(self) -> pm.TimeStepSequence:
        """
        Getter for the countries' GDP Timeseries

        :return: The GDP Timeseries for this country.
        """
        return self._gdp

    def get_sector(self, sector_id: sector.SectorIdentifier) -> sector.Sector:
        """
        Getter for the sectors of a country. Accessed by the sectors' identifier.

        :param sector_id: Identifies Sector by enum value from SectorIdentifier.
        :return: The countries sector corresponding to the sector id.
        """
        return self._sectors[sector_id]

    def get_nuts2_root(self) -> NutsRegion:
        """ Getter for the root NutsRegion. """
        return self._population.get_nuts2_root()

