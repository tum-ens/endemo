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
    _amount_per_year: Timeseries
    _amount_per_gdp: Timeseries
    _amount_per_capita_per_year: Timeseries
    _amount_per_capita_per_gdp: Timeseries

    def __init__(self, specific_consumption: SC, bat: BAT, amount_per_year: Timeseries, population: PredictedTimeseries = None,
                 gdp: TimeStepSequence = None):
        self._specific_consumption = specific_consumption
        self._bat = bat
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

    def calculate_demand(self, year: int) -> Demand:
        raise NotImplementedError


class ProductPrimSec:
    _primary: Product
    _secondary: Product
    _total: Product

    def __init__(self, specific_consumption: SC, bat: BAT, prim: Product, sec: Product, total: Product):
        super().__init__()
        self._primary = prim
        self._secondary = sec
        self._total = total

    @overrides(Product)
    def calculate_demand(self, year: int) -> Demand:
        raise NotImplementedError






