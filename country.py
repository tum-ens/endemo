from __future__ import annotations
import warnings

import containers
import industry_sector
import input
import population
import prediction_models as pm
import sector
import population as pop


class Country:
    """
    The Country connects all sectors and data from a single country. It is a completely self-contained unit.
    """
    _name: str
    _abbreviations: [str]  # not implemented yet
    _population: pop.Population[pm.PredictedTimeseries, pop.NutsRegion]
    _gdp: pm.TimeStepSequence
    _sectors: dict[sector.SectorIdentifier, sector.Sector]

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
        nuts2_root: pop.NutsRegion
        if self._abbreviations.alpha2 in nuts2_data.prognosis.keys():
            nuts2_root = pop.NutsRegion(self._abbreviations.alpha2, nuts2_data.historical[self._abbreviations.alpha2],
                                        nuts2_data.prognosis[self._abbreviations.alpha2])
        else:
            nuts2_root = pop.NutsRegion(self._abbreviations.alpha2)

        for region_name, region_data in nuts2_data.historical.items():
            if region_name == self._abbreviations.alpha2:
                continue
            # create and add subregion to root
            subregion: pop.NutsRegion
            if region_name in nuts2_data.prognosis.keys():
                subregion = pop.NutsRegion(region_name, historical_data=region_data,
                                           prediction_data=nuts2_data.prognosis[region_name])
            else:
                subregion = pop.NutsRegion(region_name, historical_data=region_data)
            nuts2_root.add_child_region(subregion)

        # fill population member variable
        self._population = pop.Population(country_population, nuts2_root,
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

        # Future TODO: add other sectors

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

    def calculate_total_demand(self, year: int) -> containers.Demand:
        total_demand = containers.Demand()

        for sector_name, obj_sector in self._sectors.items():
            total_demand.add(obj_sector.calculate_total_demand(year))

        return total_demand

    def get_name(self):
        return self._name

    def get_population(self) -> population.Population:
        return self._population

    def get_gdp(self):
        return self._gdp

    def get_sector(self, sector_id: sector.SectorIdentifier):
        return self._sectors[sector_id]
