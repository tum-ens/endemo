from __future__ import annotations

import warnings
from collections import namedtuple

import utility as uty
import input
import output
import prediction_models as pm
import control_parameters as cp
import population as pop

SC = namedtuple("SC", ["electricity", "heat", "hydrogen", "max_subst_h2"])
BAT = namedtuple("BAT", ["electricity", "heat"])


class SpecificConsumptionData:
    """
    Holds all consumption data for one product within an industry of a country.
    """
    default_specific_consumption: SC
    historical_specific_consumption: dict[str, pm.Timeseries]
    efficiency: dict[str, BAT]
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
            return self.default_specific_consumption


class Product:
    """
    Holds all information and objects belonging to a product in the industry of a country.
    """
    _name: str
    _country_name: str
    _specific_consumption: SpecificConsumptionData
    _bat: BAT
    _perc_used: float
    _exp_change_rate: float
    _heat_levels: output.Heat
    _amount_per_year: pm.Timeseries
    _amount_per_gdp: pm.Timeseries
    _amount_per_capita_per_year: pm.Timeseries
    _amount_per_capita_per_gdp: pm.Timeseries

    _use_per_capita: bool
    _use_gdp_as_x: bool

    _empty_product: bool

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

        # read bat consumption for product in countries industry
        if country_name in product_input.bat.keys():
            self._bat = product_input.bat[country_name]
        else:
            self._bat = product_input.bat["all"]

        # read historical production data
        if country_name in product_input.production.keys() \
                and not uty.is_tuple_list_zero(product_input.production[country_name]):
            self._empty_product = False
            self._amount_per_year = \
                pm.Timeseries(product_input.production[country_name], industry_settings.forecast_method,
                              rate_of_change=self._exp_change_rate)
        else:
            # warnings.warn("Country " + country_name + " has no production data for " + product_name)
            self._empty_product = True
            self._specific_consumption = SpecificConsumptionData(product_input)
            return

        # calculate rest of member variables
        zipped_data = list(uty.zip_on_x(self._amount_per_year.get_data(), population.get_data()))
        self._amount_per_capita_per_year = \
            pm.Timeseries(list(map(lambda arg: (arg[0][0], arg[0][1] / arg[1][1]), zipped_data)),
                          industry_settings.forecast_method, rate_of_change=self._exp_change_rate)
        self._amount_per_gdp = \
            pm.Timeseries(uty.combine_data_on_x(gdp.get_data(), self._amount_per_year.get_data(), ascending_x=True),
                          industry_settings.forecast_method, rate_of_change=self._exp_change_rate)
        zipped_data = list(uty.zip_on_x(gdp.get_data(), population.get_data()))
        self._amount_per_capita_per_gdp = \
            pm.Timeseries(list(map(lambda arg: (arg[0][0], arg[0][1] / arg[1][1]), zipped_data)),
                          industry_settings.forecast_method, rate_of_change=self._exp_change_rate)

        # read specific consumption data
        self._specific_consumption = SpecificConsumptionData(product_amount_per_year=self._amount_per_year,
                                                             country_name=country_name, product_input=product_input,
                                                             input_manager=input_manager)

        if country_name == "Greece" and product_name == "cement":
            uty.plot_timeseries(self._amount_per_year)
            uty.plot_timeseries(self._amount_per_capita_per_year)

    def split_heat_levels(self, x: float) -> (float, float, float, float):
        heat = self._heat_levels
        heat.mutable_multiply_scalar(x)

    def calculate_demand(self, year: int) -> output.Demand:
        if self._empty_product:
            return output.Demand()

        sc = self._specific_consumption.get(year)
        perc = self._perc_used

        # choose which type of amount based on settings
        amount = self.get_amount_prog(year)

        # calculate demand after all variables are available
        cached_perc_amount = perc * amount
        electricity = cached_perc_amount * sc.electricity
        hydrogen = cached_perc_amount * sc.hydrogen

        heat = self._heat_levels
        heat.mutable_multiply_scalar(cached_perc_amount * sc.heat)   # separate heat levels

        return output.Demand(electricity, heat, hydrogen)

    def get_amount_prog(self, year: int) -> float:
        if self._empty_product:
            return 0

        prog_amount = 0

        if not self._use_per_capita and not self._use_gdp_as_x:
            prog_amount = self._amount_per_year.get_prog(year)
        elif self._use_per_capita and not self._use_gdp_as_x:
            prog_amount = self._amount_per_capita_per_year.get_prog(year)
        elif not self._use_per_capita and self._use_gdp_as_x:
            prog_amount = self._amount_per_gdp.get_prog(year)
        elif self._use_per_capita and self._use_gdp_as_x:
            prog_amount = self._amount_per_capita_per_gdp.get_prog(year)

        prog_amount = max(0, prog_amount)
        return prog_amount

    def get_coef(self) -> pm.Coef:
        if self._empty_product:
            return pm.Coef()
        if not self._use_per_capita and not self._use_gdp_as_x:
            return self._amount_per_year.get_coef()
        elif self._use_per_capita and not self._use_gdp_as_x:
            return self._amount_per_capita_per_year.get_coef()
        elif not self._use_per_capita and self._use_gdp_as_x:
            return self._amount_per_gdp.get_coef()
        elif self._use_per_capita and self._use_gdp_as_x:
            return self._amount_per_capita_per_gdp.get_coef()

    def get_active_timeseries(self) -> pm.Timeseries:
        if self._empty_product:
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

    def calculate_demand(self, year: int) -> output.Demand:
        raise NotImplementedError
