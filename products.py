from __future__ import annotations
from collections import namedtuple

import pandas as pd
from debugpy._vendored.pydevd._pydev_bundle.pydev_override import overrides

import utility as uty
from output import Demand
from prediction_models import Timeseries, PredictedTimeseries, TimeStepSequence

SC = namedtuple("SC", ["electricity", "heat", "hydrogen", "max_subst_h2"])
BAT = namedtuple("BAT", ["electricity", "heat"])


class Product:
    _specific_consumption: SC
    _bat: BAT
    _perc_used: float
    _exp_change_rate: float

    def __init__(self, specific_consumption: SC, bat: BAT):
        self._specific_consumption = specific_consumption
        self._bat = bat

    def calculate_demand(self, year: int) -> Demand:
        raise NotImplementedError


class ProductHistorical(Product):
    _amount_per_year: Timeseries
    _amount_per_gdp: Timeseries
    _amount_per_capita_per_year: Timeseries
    _amount_per_capita_per_gdp: Timeseries

    def __init__(self, specific_consumption: SC, bat: BAT, amount_per_year: Timeseries, population: PredictedTimeseries = None,
                 gdp: TimeStepSequence = None):
        super().__init__(specific_consumption, bat)
        self._amount_per_year = amount_per_year

        if population:
            zipped = list(uty.zip_on_x(self._amount_per_year.get_data(), population.get_data()))
            _amount_per_capita_per_year = \
                Timeseries(list(map(lambda arg: (arg[0][0], arg[0][1] / arg[1][1]), zipped)))

        if gdp:
            self._amount_per_gdp = uty.combine_data_on_x(amount_per_year.get_data(), gdp.get_data(), ascending_x=True)
            if population:
                zipped = list(uty.zip_on_x(self._amount_per_gdp.get_data(), population.get_data()))
                _amount_per_capita_per_gdp = \
                    Timeseries(list(map(lambda arg: (arg[0][0], arg[0][1] / arg[1][1]), zipped)))

    @overrides(Product)
    def calculate_demand(self, year: int) -> Demand:
        # multiply by perc_used in the end
        raise NotImplementedError


class ProductPrimSec(Product):
    _primary: ProductHistorical
    _secondary: ProductHistorical
    _total: ProductHistorical

    def __init__(self, specific_consumption: SC, bat: BAT, prim: ProductHistorical, sec: ProductHistorical, total: ProductHistorical):
        super().__init__()
        self._primary = prim
        self._secondary = sec
        self._total = total

    @overrides(Product)
    def calculate_demand(self, year: int) -> Demand:
        raise NotImplementedError


class ProductFutureTech(Product):
    _historical_counterpart: ProductHistorical

    @overrides(Product)
    def calculate_demand(self, year: int) -> Demand:
        raise NotImplementedError









