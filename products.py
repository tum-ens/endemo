from __future__ import annotations

import warnings
from collections import namedtuple

import utility as uty
import input
import output
import prediction_models as pm

SC = namedtuple("SC", ["electricity", "heat", "hydrogen", "max_subst_h2"])
BAT = namedtuple("BAT", ["electricity", "heat"])


class Product:
    _name: str
    _country_name: str
    _specific_consumption: SC
    _bat: BAT
    _perc_used: float
    _exp_change_rate: float
    _amount_per_year: pm.Timeseries
    _amount_per_gdp: pm.Timeseries
    _amount_per_capita_per_year: pm.Timeseries
    _amount_per_capita_per_gdp: pm.Timeseries

    def __init__(self, product_name: str, product_input: input.IndustryInput.ProductInput,
                 country_name: str, population: pm.PredictedTimeseries = None, gdp: pm.TimeStepSequence = None):
        self._country_name = country_name
        self._name = product_name

        # read specific consumption for product in countries industry
        if country_name in product_input.specific_consumption.keys():
            self._specific_consumption = product_input.specific_consumption[country_name]
        else:
            self._specific_consumption = product_input.specific_consumption["all"]

        # read bat consumption for product in countries industry
        if country_name in product_input.bat.keys():
            self._bat = product_input.bat[country_name]
        else:
            self._bat = product_input.bat["all"]

        # read historical production data
        if country_name in product_input.production.keys() \
                and not uty.is_zero(list(zip(*product_input.production[country_name]))[1]):
            self._amount_per_year = \
                pm.Timeseries(product_input.production[country_name], pm.CalculationType.LINEAR)
        else:
            # warnings.warn("Country " + country_name + " has no production data for " + product_name)
            return

        # calculate rest of member variables
        if population:
            zipped = list(uty.zip_on_x(self._amount_per_year.get_data(), population.get_data()))
            self._amount_per_capita_per_year = \
                pm.Timeseries(list(map(lambda arg: (arg[0][0], arg[0][1] / arg[1][1]), zipped)),
                              pm.CalculationType.LINEAR)

        if gdp:
            self._amount_per_gdp = \
                pm.Timeseries(uty.combine_data_on_x(gdp.get_data(), self._amount_per_year.get_data(), ascending_x=True),
                              pm.CalculationType.QUADRATIC)
            if population:
                zipped = list(uty.zip_on_x(gdp.get_data(), population.get_data()))
                _amount_per_capita_per_gdp = \
                    pm.Timeseries(list(map(lambda arg: (arg[0][0], arg[0][1] / arg[1][1]), zipped)),
                                  pm.CalculationType.LINEAR)

    def calculate_demand(self, year: int) -> output.Demand:
        raise NotImplementedError


class ProductPrimSec:
    _primary: Product
    _secondary: Product
    _total: Product

    def __init__(self, prim: Product, sec: Product, total: Product):
        self._primary = prim
        self._secondary = sec
        self._total = total

    def calculate_demand(self, year: int) -> output.Demand:
        raise NotImplementedError
