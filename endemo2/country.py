from __future__ import annotations
import warnings

from endemo2 import containers, industry_sector, input, sector, containers as ctn, utility as uty
from endemo2 import prediction_models as pm


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

    def calculate_total_demand(self, year: int) -> containers.Demand:
        """
        Sum the demand over all sectors of the country.

        :param year: Target year for which the prediction should be calculated.
        :return: The demand for a country summed over all sectors.
        """
        total_demand = containers.Demand()

        for sector_name, obj_sector in self._sectors.items():
            total_demand.add(obj_sector.calculate_total_demand(year))

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


class Population:
    """
    Holds information about a countries' population. Contains per-country data, as well as nuts2 data

    :ivar PredictedTimeseries country_level_population: The timeseries containing population information and predictions
        on a country level.
    :ivar NutsRegion nuts2: The root of the Nuts2 Tree for a country.
    :ivar bool nuts2_used: Decides, which type of population should be used for getters.
    """

    def __init__(self, country_level_population: pm.PredictedTimeseries, nuts2: NutsRegion, nuts2_used: bool):
        self.country_level_population = country_level_population
        self.nuts2 = nuts2
        self.nuts2_used = nuts2_used

    def get_data(self) -> [(float, float)]:
        """
        Getter for data based on whether nuts2_used is true or not.

        :return: Nuts2 population data if nuts2_used is true, otherwise country level data.
        """
        if self.nuts2_used and self.nuts2:
            return self.nuts2.get_historical_data()
        else:
            return self.country_level_population.get_data()

    def get_country_historical_data(self) -> [(float, float)]:
        """ Getter for the country-level historical data. """
        return self.country_level_population.get_data()

    def get_prog(self, year: int) -> float:
        """
        Getter for population prognosis based on whether nuts2_used is true or not.

        :return: Nuts2 population prognosis if nuts2_used is true, otherwise country level data.
        """
        if self.nuts2_used and self.nuts2:
            return self.nuts2.get_pop_prog(year)
        else:
            return self.country_level_population.get_prog(year)

    def get_country_prog(self, year: int) -> float:
        """ Getter for the country-level prognosis. """
        return self.country_level_population.get_prog(year)

    def get_nuts2_prog(self, year: int) -> float:
        """ Getter for the nuts2 prognosis. """
        return self.nuts2.get_pop_prog(year)

    def get_nuts2_root(self) -> NutsRegion:
        """ Getter for the nuts2 regions root node object. """
        return self.nuts2


class NutsRegion:
    """
    Represents one NUTS Region according to individual codes.
    It is build as a tree structure to include sub-regions as child nodes. The leafs are NUTS2 regions.

    :ivar str region_name: The NUTS tag of the region. For example: DE, DE1, DE11, ...
    :ivar dict[str, NutsRegion] _subregions: The child regions, accessible per NUTS tag. For DE: {DE1 -> .., DE2 -> ..}
    :ivar Timeseries _ts_population: The timeseries for the regions population. Should only be filled for leaf nodes.
    :ivar [(float, float)] _population_historical: The historical population for this region.
        Should only be filled for leaf nodes.
    """

    def __init__(self, region_name, historical_data: [(float, float)] = None,
                 prediction_data: (ctn.Interval, float) = None):
        self.region_name = region_name
        self._sub_regions = dict()
        self._population_historical = historical_data

        if prediction_data is not None and historical_data is not None:
            self._ts_population = pm.TimeStepSequence(historical_data, prediction_data)
        elif historical_data is not None and prediction_data is None:
            warnings.warn("For region " + self.region_name + "there was no prediction data. Using Linear Regression "
                                                             "instead.")
            self._ts_population = pm.Timeseries(historical_data, prediction_data)

    def __str__(self):
        if len(self._sub_regions.items()) < 1:
            out = "[leaf: " + self.region_name + "]"
        else:
            out = "[root: " + self.region_name + ", children: "
            for key, value in self._sub_regions.items():
                out += key + ", "
            out += "]"
            for _, child in self._sub_regions.items():
                out += str(child)
        return out

    def add_child_region(self, nuts2region_obj: NutsRegion) -> None:
        """
        Traverses the NUTS Tree recursively to insert region node.

        :param nuts2region_obj: The NutsRegion object to insert into the tree
        """
        if len(self.region_name) + 1 is len(nuts2region_obj.region_name):
            # region is direct subregion
            self._sub_regions[nuts2region_obj.region_name] = nuts2region_obj
        elif len(self.region_name) + 1 < len(nuts2region_obj.region_name):
            # region is a subregion of a subregion, search for right one to insert
            for key, value in self._sub_regions.items():
                if nuts2region_obj.region_name.startswith(key):
                    # found parent region
                    self._sub_regions[key].add_child_region(nuts2region_obj)
                    return
            # found no region, create in-between
            new_inbetween_region_name = nuts2region_obj.region_name[:len(self.region_name)+1]
            self._sub_regions[new_inbetween_region_name] = NutsRegion(new_inbetween_region_name)
            self._sub_regions[new_inbetween_region_name].add_child_region(nuts2region_obj)

    def get_historical_data(self) -> [(float, float)]:
        """
        Get historical data or sum over subregions if not available.

        :return: The historical population amount for this region.
        """
        if self._population_historical is None:
            subregion_objs = list(self._sub_regions.values())
            result = subregion_objs[0].get_historical_data()
            for subregion_obj in subregion_objs[1:]:
                result = list(uty.zip_on_x(result, subregion_obj.get_historical_data()))
                result = [(x1, y1 + y2) for ((x1, y1), (x2, y2)) in result]
            self._population_historical = result
        return self._population_historical

    def get_pop_prog(self, year: int) -> float:
        """
        Recursively calculate and sum up the prognosis for all leaf regions.

        :return: The population amount prognosis for this region.
        """
        result = 0
        if len(self._sub_regions) != 0:
            for subregion in self._sub_regions.values():
                result += subregion.get_pop_prog(year)
            return result
        else:
            return self._ts_population.get_prog(year)

    def get_nodes_dfs(self) -> [NutsRegion]:
        """
        Get a list of all nodes in Depth-First-Search order.

        :return: The list of nodes in DFS-order.
        """
        if len(self._sub_regions) == 0:
            # leaf node, return only self
            return [self]
        else:
            # recursively return this node and all children
            nodes = [self]
            for subregion in self._sub_regions.values():
                nodes += subregion.get_nodes_dfs()
            return nodes
