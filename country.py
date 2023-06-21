import warnings

import industry_sector
import input
import output
import prediction_models as pm
import sector


class Country:
    """
    The Country connects all sectors and data from a single country. It is a completely self-contained unit.
    """
    _name: str
    _abbreviations: [str]  # not implemented yet
    _population: pm.PredictedTimeseries
    _gdp: pm.TimeStepSequence
    _sectors: dict[sector.SectorIdentifier, sector.Sector]

    def __init__(self, name: str, input_manager: input.Input):
        self._name = name
        self._sectors = dict()

        # fill abbreviations
        self._abbreviations = input_manager.general_input.abbreviations[self._name]

        # create population timeseries
        self._population = \
            pm.PredictedTimeseries(
                historical_data=input_manager.general_input.population.country_population[self._name].historical,
                prediction_data=input_manager.general_input.population.country_population[self._name].prognosis)

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
        if not self._population.get_data():
            warnings.warn("Country " + self._name + " has an empty list of historical Population.")
        if not self._population.get_prediction_raw():
            warnings.warn("Country " + self._name + " has an empty list of prediction for Population.")
        if not self._gdp.get_historical_data_raw():
            warnings.warn("Country " + self._name + " has an empty list of historical gdp.")
        if not self._gdp.get_interval_change_rate_raw():
            warnings.warn("Country " + self._name + " has an empty list of interval_changeRate for gdp.")

    def calculate_total_demand(self, year: int) -> output.Demand:
        total_demand = output.Demand()

        for sector_name, obj_sector in self._sectors.items():
            total_demand.add(obj_sector.calculate_total_demand(year))

        return total_demand

    def get_name(self):
        return self._name

    def get_population(self):
        return self._population

    def get_gdp(self):
        return self._gdp

    def get_sector(self, sector_id: sector.SectorIdentifier):
        return self._sectors[sector_id]

class NutsRegion:
    """
    Represents one NUTS2 Region according to individual codes.
    It is build as a tree structure to include sub-regions as child nodes.
    """
    region_name: str
    _sub_regions = dict()    # str -> NutsRegion (python doesn't allow to indicate the type directly)
    _population: pm.TimeStepSequence

    def __init__(self, region_name, historical_data: [(float, float)], prediction_data: (pm.Interval, float)):
        self.region_name = region_name
        self.historical_data = historical_data

        self._population = pm.TimeStepSequence(historical_data, [prediction_data])

    def add_child_region(self, region_name: str, nuts2region_obj):
        """ Traverses the NUTS Tree recursively to insert region node. """
        if len(self.region_name) + 1 is len(region_name):
            # region is direct subregion
            self._sub_regions[region_name] = nuts2region_obj
            return
        elif len(self.region_name) + 1 < len(region_name):
            # region is a subregion of a subregion, search for right one to insert
            for key, value in self._sub_regions.items():
                if region_name.startswith(key):
                    # found parent region
                    self._sub_regions[key].add_child_region(region_name, nuts2region_obj)
                    return
        warnings.warn("Something went wrong when trying to insert the nuts2 subregion " + region_name)

    def get_pop_prog(self, year: int) -> float:
        """ Recursively calculate and sum up the prognosis for all leaf regions"""
        result = 0
        if len(self._sub_regions) is not 0:
            for subregion in self._sub_regions.values():
                result += subregion.get_pop_prog(year)
            return result
        else:
            return self._population.get_prog(year)



