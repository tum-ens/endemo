from __future__ import annotations

import numpy as np

import utility as uty
import input
import prediction_models as pm
import control_parameters as cp
import population as pop
from containers import EH, Heat, Demand, SC


class Product:
    """
    Holds all information and objects belonging to a product in the industry of a country.
    """
    _name: str
    _country_name: str
    _specific_consumption: SpecificConsumptionData
    _bat: EH
    _perc_used: float
    _exp_change_rate: float
    _heat_levels: Heat
    _amount_per_year: pm.Timeseries
    _amount_per_gdp: pm.Timeseries
    _amount_per_capita_per_year: pm.Timeseries
    _amount_per_capita_per_gdp: pm.Timeseries

    _use_per_capita: bool
    _use_gdp_as_x: bool

    _empty: bool

    def __init__(self, product_name: str, product_input: input.IndustryInput.ProductInput, input_manager: input.Input,
                 country_name: str, population: pop.Population, gdp: pm.TimeStepSequence):

        self._country_name = country_name
        self._name = product_name
        self._heat_levels = product_input.heat_levels
        self._perc_used = product_input.perc_used
        self._exp_change_rate = product_input.manual_exp_change_rate

        # get information from industry settings
        industry_settings = input_manager.industry_input.settings
        self._use_per_capita = industry_settings.production_quantity_calc_per_capita
        self._use_gdp_as_x = True if industry_settings.forecast_method == cp.ForecastMethod.QUADRATIC else False
        forecast_method = input_manager.ctrl.industry_settings.forecast_method

        # read bat consumption for product in countries industry
        if country_name in product_input.bat.keys():
            self._bat = product_input.bat[country_name]
        else:
            self._bat = product_input.bat["all"]

        # read historical production data
        if country_name in product_input.production.keys() \
                and not uty.is_tuple_list_zero(product_input.production[country_name]):
            self._empty = False
            self._amount_per_year = \
                pm.Timeseries(product_input.production[country_name], forecast_method,
                              rate_of_change=self._exp_change_rate)
        else:
            # warnings.warn("Country " + country_name + " has no production data for " + product_name)
            self._empty = True
            self._specific_consumption = SpecificConsumptionData(product_input)
            return

        # calculate rest of member variables
        zipped_data = list(uty.zip_on_x(self._amount_per_year.get_data(), population.get_country_historical_data()))
        self._amount_per_capita_per_year = \
            pm.Timeseries(list(map(lambda arg: (arg[0][0], arg[0][1] / arg[1][1]), zipped_data)),
                          forecast_method, rate_of_change=self._exp_change_rate)
        self._amount_per_gdp = \
            pm.Timeseries(uty.combine_data_on_x(gdp.get_data(), self._amount_per_year.get_data(), ascending_x=True),
                          forecast_method, rate_of_change=self._exp_change_rate)
        zipped_data = list(uty.zip_on_x(gdp.get_data(), population.get_country_historical_data()))
        self._amount_per_capita_per_gdp = \
            pm.Timeseries(list(map(lambda arg: (arg[0][0], arg[0][1] / arg[1][1]), zipped_data)),
                          forecast_method, rate_of_change=self._exp_change_rate)

        # read specific consumption data
        self._specific_consumption = SpecificConsumptionData(product_amount_per_year=self._amount_per_year,
                                                             country_name=country_name, product_input=product_input,
                                                             input_manager=input_manager)


    def is_empty(self) -> bool:
        return self._empty

    def is_per_capita(self) -> bool:
        return self._use_per_capita

    def is_per_gdp(self) -> bool:
        return self._use_gdp_as_x

    def get_timeseries_amount_per_year(self):
        if self._empty:
            return pm.Timeseries([], cp.ForecastMethod.LINEAR)
        return self._amount_per_year

    def get_timeseries_amount_per_gdp(self):
        if self._empty:
            return pm.Timeseries([], cp.ForecastMethod.LINEAR)
        return self._amount_per_gdp

    def get_timeseries_amount_per_capita_per_year(self):
        if self._empty:
            return pm.Timeseries([], cp.ForecastMethod.LINEAR)
        return self._amount_per_capita_per_year

    def get_timeseries_amount_per_capita_per_gdp(self):
        if self._empty:
            return pm.Timeseries([], cp.ForecastMethod.LINEAR)
        return self._amount_per_capita_per_gdp

    def split_heat_levels(self, x: float) -> (float, float, float, float):
        heat = self._heat_levels
        heat.mutable_multiply_scalar(x)

    def calculate_demand(self, year: int) -> Demand:
        if self._empty:
            return Demand()

        sc = self._specific_consumption.get_scale(year, 1/3600000)    # get SC and convert from GJ/T to TWH/T
        perc = self._perc_used

        # choose which type of amount based on settings
        amount = self.get_amount_prog(year) * 1000      # convert kT to T

        # calculate demand after all variables are available
        cached_perc_amount = perc * amount
        electricity = cached_perc_amount * sc.electricity
        hydrogen = cached_perc_amount * sc.hydrogen

        heat = self._heat_levels.copy_multiply_scalar(cached_perc_amount * sc.heat)     # separate heat levels

        return Demand(electricity, heat, hydrogen)

    def get_amount_prog(self, year: int) -> float:
        if self._empty:
            return 0.0
        active_timeseries = self.get_active_timeseries()
        prog_amount = max(0.0, active_timeseries.get_prog(year))
        return prog_amount

    def get_coef(self) -> pm.Coef:
        if self._empty:
            return pm.Coef()
        active_timeseries = self.get_active_timeseries()
        return active_timeseries.get_coef()

    def get_active_timeseries(self) -> pm.Timeseries:
        if self._empty:
            return pm.Timeseries([], cp.ForecastMethod.LINEAR)
        if not self._use_per_capita and not self._use_gdp_as_x:
            return self._amount_per_year
        elif self._use_per_capita and not self._use_gdp_as_x:
            return self._amount_per_capita_per_year
        elif not self._use_per_capita and self._use_gdp_as_x:
            return self._amount_per_gdp
        elif self._use_per_capita and self._use_gdp_as_x:
            return self._amount_per_capita_per_gdp

    def get_specific_consumption(self) -> SpecificConsumptionData:
        return self._specific_consumption


class ProductPrimSec:
    _primary: Product
    _secondary: Product
    _total: Product

    def __init__(self, prim: Product, sec: Product, total: Product):
        self._primary = prim
        self._secondary = sec
        self._total = total

    def calculate_demand(self, year: int) -> Demand:
        raise NotImplementedError


class SpecificConsumptionData:
    """
    Holds all consumption data for one product within an industry of a country.
    """
    default_specific_consumption: SC
    historical_specific_consumption: dict[str, pm.Timeseries]
    efficiency: dict[str, EH]
    _product_amount_per_year: pm.Timeseries
    _calculate_sc: bool

    def __init__(self, product_input: input.IndustryInput.ProductInput, product_amount_per_year: pm.Timeseries = None,
                 country_name: str = "",
                 input_manager: input.Input = None):
        if product_amount_per_year is None:
            self.default_specific_consumption = product_input.specific_consumption_default["all"]
            self._calculate_sc = False
            return

        self.historical_specific_consumption = dict[str, pm.Timeseries]()
        self._product_amount_per_year = product_amount_per_year
        self._calculate_sc = input_manager.industry_input.settings.trend_calc_for_spec

        # get efficiency
        self.efficiency = input_manager.general_input.efficiency

        # read default specific consumption for product in countries industry
        if country_name in product_input.specific_consumption_default.keys():
            self.default_specific_consumption = product_input.specific_consumption_default[country_name]
        else:
            self.default_specific_consumption = product_input.specific_consumption_default["all"]

        # read historical specific consumption data
        if country_name in product_input.specific_consumption_historical:
            dict_sc_his = product_input.specific_consumption_historical[country_name]
            for key, value in dict_sc_his.items():
                self.historical_specific_consumption[key] = pm.Timeseries(value, cp.ForecastMethod.LINEAR)
        else:
            self._calculate_sc = False

    def get_scale(self, year, scalar) -> SC:
        sc = self.get(year)
        return SC(sc.electricity * scalar, sc.heat * scalar, sc.hydrogen * scalar, sc.max_subst_h2)

    def get(self, year) -> SC:
        """ Returns the specific consumption """
        if self._calculate_sc and self.historical_specific_consumption:
            electricity = 0
            heat = 0.0
            for key, value in self.historical_specific_consumption.items():
                prog_amount = value.get_prog(year) / self._product_amount_per_year.get_prog(year)
                electricity += prog_amount * self.efficiency[key].electricity
                heat += prog_amount * self.efficiency[key].heat
            return SC(electricity, heat, 0, 0)
        else:
            # future TODO: add efficiency to default specific consumption
            return self.default_specific_consumption
