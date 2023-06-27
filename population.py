from __future__ import annotations
import warnings
import prediction_models as pm
import control_parameters as ctrl


class Population:
    country_level_population: pm.PredictedTimeseries
    nuts2: NutsRegion
    nuts2_used: bool

    def __init__(self, country_level_population: pm.PredictedTimeseries, nuts2: NutsRegion, nuts2_used: bool):
        self.country_level_population = country_level_population
        self.nuts2 = nuts2
        self.nuts2_used = nuts2_used

    def get_data(self):
        if self.nuts2_used and self.nuts2:
            return self.nuts2.historical_data
        else:
            return self.country_level_population.get_data()

    def get_prog(self, year: int):
        if self.nuts2_used and self.nuts2:
            return self.nuts2.get_pop_prog(year)
        else:
            return self.country_level_population.get_prog(year)


class NutsRegion:
    """
    Represents one NUTS2 Region according to individual codes.
    It is build as a tree structure to include sub-regions as child nodes.
    """
    region_name: str
    _sub_regions: dict[str, NutsRegion]
    _population: pm.Timeseries

    def __init__(self, region_name, historical_data: [(float, float)], prediction_data: (pm.Interval, float) = None):
        self.region_name = region_name
        self._sub_regions = dict()
        self.historical_data = historical_data

        if prediction_data is None:
            self._population = pm.Timeseries(historical_data, ctrl.ForecastMethod.LINEAR)
        else:
            self._population = pm.TimeStepSequence(historical_data, prediction_data)

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

    def add_child_region(self, nuts2region_obj):
        """ Traverses the NUTS Tree recursively to insert region node. """
        if len(self.region_name) + 1 is len(nuts2region_obj.region_name):
            # region is direct subregion
            self._sub_regions[nuts2region_obj.region_name] = nuts2region_obj
            return
        elif len(self.region_name) + 1 < len(nuts2region_obj.region_name):
            # region is a subregion of a subregion, search for right one to insert
            for key, value in self._sub_regions.items():
                if nuts2region_obj.region_name.startswith(key):
                    # found parent region
                    self._sub_regions[key].add_child_region(nuts2region_obj)
                    return
        warnings.warn("Something went wrong when trying to insert the nuts2 subregion " + nuts2region_obj.region_name)

    def get_pop_prog(self, year: int) -> float:
        """ Recursively calculate and sum up the prognosis for all leaf regions"""
        result = 0
        if len(self._sub_regions) != 0:
            for subregion in self._sub_regions.values():
                result += subregion.get_pop_prog(year)
            return result
        else:
            return self._population.get_prog(year)




