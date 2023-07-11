from __future__ import annotations

from endemo2 import utility as uty
from endemo2 import input
from endemo2 import prediction_models as pm
from endemo2 import control_parameters as cp
from endemo2 import population as pop
from endemo2 import containers as ctn


class Product:
    """
    Holds all information and objects belonging to a product in the industry of a country.

    :param product_name: The name of the product type. For example "steel_prim".
    :param product_input: The product types input from the input manager. (Redundant)
    :param input_manager: The input manager, which holds all input data used to create this product.
    :param country_name: The name of the country to whose industry this product belongs to.
    :param population: The countries population amount used to create timeseries per capita.
    :param gdp: The countries gdp used to create timeseries per gdp.

    :ivar str _name: The name of the product. For example "steel_prim".
    :ivar str _country_name: The name of the country to whose industry this product belongs to.

    :ivar SpecificConsumptionData _specific_consumption: The object used to optionally calculate and get the specific
        consumption amounts for this product type.
    :ivar EH _bat: The specific consumption of the best available technology.
    :ivar float _perc_used: The percentage of the predicted amount used of this product. Can be configured to model new
        technology replacing old ones.
    :ivar float _exp_change_rate: The manual change rate for the exponential forecast method.
    :ivar Heat _heat_levels: The heat levels, that splits the forecasted heat demand into demand at different heat
        levels, by using fixed percentages.

    :ivar Timeseries _amount_per_year: Used to predict the product amount. The x-axis is time in years.
    :ivar Timeseries _amount_per_gdp: Used to predict the product amount. The x-axis is the countries' gdp.
    :ivar Timeseries _amount_per_capita_per_year: Used to predict the product amount per capita.
        The x-axis is time in years.
    :ivar Timeseries _amount_per_capita_per_gdp: Used to predict the product amount per capita.
        The x-axis is time in years.

    :ivar bool _use_per_capita: Indicates whether the timeseries that predict amount per capita should be used for the
        forecast.
    :ivar bool _use_gdp_as_x: Indicated whether the timeseries that use the gdp as x-axis should be used for the
        forecast.
    :ivar bool _empty: Indicates that the product historical data is empty. This is true, if the country is being
        present in the input table but filters causing the list to be empty.
    """

    def __init__(self, product_name: str, product_input: input.ProductInput, input_manager: input.Input,
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
            self._amount_per_year = pm.Timeseries([], forecast_method)
            self._amount_per_capita_per_year = pm.Timeseries([], forecast_method)
            self._amount_per_gdp = pm.Timeseries([], forecast_method)
            self._amount_per_capita_per_gdp = pm.Timeseries([], forecast_method)
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
        """ Getter for the _empty attribute. """
        return self._empty

    def is_per_capita(self) -> bool:
        """ Getter for the _use_per_capita attribute. """
        return self._use_per_capita

    def is_per_gdp(self) -> bool:
        """ Getter for the _use_gdp_as_x attribute. """
        return self._use_gdp_as_x

    def get_timeseries_amount_per_year(self):
        """ Getter for the _amount_per_year timeseries. """
        return self._amount_per_year

    def get_timeseries_amount_per_gdp(self):
        """ Getter for the _amount_per_gdp timeseries. """
        return self._amount_per_gdp

    def get_timeseries_amount_per_capita_per_year(self):
        """ Getter for the _amount_per_capita_per_year timeseries. """
        return self._amount_per_capita_per_year

    def get_timeseries_amount_per_capita_per_gdp(self):
        """ Getter for the _amount_per_capita_per_gdp timeseries. """
        return self._amount_per_capita_per_gdp

    def split_heat_levels(self, x: float) -> (float, float, float, float):
        """
        Takes amount of heat as input and splits it into different heat levels, according to the _heat_levels attribute.

        :param float x: The amount of heat to be split into different heat levels.
        :return: The amount of heat in different heat levels as a tuple: (Q1, Q2, Q3, Q4)
        """
        heat = self._heat_levels
        heat.mutable_multiply_scalar(x)

    def calculate_demand(self, year: int) -> ctn.Demand:
        """
        Calculates the demand for this product. Returns zero demand when the _empty attribute is true.

        .. math::
            D(y)[TWh/T] = p*A(y)[T]*(c_{electricity}, c_{heat_{split}}, c_{hydrogen})[TWh/T]

        :param year: The target year, the demand should be calculated for.
        :return: The calculated demand.
        """
        if self._empty:
            return ctn.Demand()

        sc = self._specific_consumption.get_scale(year, 1/3600000)    # get SC and convert from GJ/T to TWH/T
        perc = self._perc_used

        # choose which type of amount based on settings
        amount = self.get_amount_prog(year) * 1000      # convert kT to T

        # calculate demand after all variables are available
        cached_perc_amount = perc * amount
        electricity = cached_perc_amount * sc.electricity
        hydrogen = cached_perc_amount * sc.hydrogen

        heat = self._heat_levels.copy_multiply_scalar(cached_perc_amount * sc.heat)     # separate heat levels

        return ctn.Demand(electricity, heat, hydrogen)

    def get_amount_prog(self, year: int) -> float:
        """
        Get the prognosis for the amount of this product in a certain year according to current settings regarding gdp
            and per_capita calculation.
        :param year:
        :return: The estimated product amount for given year.
        """
        if self._empty:
            return 0.0
        active_timeseries = self.get_active_timeseries()
        prog_amount = max(0.0, active_timeseries.get_prog(year))
        return prog_amount

    def get_coef(self) -> pm.Coef:
        """ Getter for the coefficients of the currently used timeseries according to settings. """
        active_timeseries = self.get_active_timeseries()
        return active_timeseries.get_coef()

    def get_active_timeseries(self) -> pm.Timeseries:
        """
        Getter for the current timeseries according to current settings regarding gdp
        and per_capita calculation.
        """
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
        """ Getter for the specific consumption object. """
        return self._specific_consumption


class ProductPrimSec:
    """
    A container for products that are split into primary and secondary.

    :ivar Product _primary: The primary product.
    :ivar Product _secondary: The secondary product.
    :ivar Product _total: A product merging the primary and secondary products.
    :todo: Actually use this somewhere.
    """

    def __init__(self, prim: Product, sec: Product, total: Product):
        self._primary = prim
        self._secondary = sec
        self._total = total

    def calculate_demand(self, year: int) -> ctn.Demand:
        raise NotImplementedError


class SpecificConsumptionData:
    """
    Holds all consumption data for one product within an industry of a country.


    :param Input input_manager: The input manager, containing information needed to create this object.
    :param ProductInput product_input: The input for this specific product type, needed to create it. (Redundant)
    :param Timeseries product_amount_per_year: The timeseries object from the product to get the predicted product
        amount, used in calculations. (Redundant, but used to prevent circular dependencies)
    :param str country_name: Name of the country, this product belongs to.

    :ivar SC default_specific_consumption: The specific consumption for a product type, that is used as default if
        there is no historical data to predict the specific consumption.
    :ivar dict[str, Timeseries] historical_specific_consumption: The historical data for specific consumption according
        to energy carrier.
    :ivar dict[str, EH] efficiency: Efficiency of each energy carrier in percent in [0,1].
    :ivar Timeseries _product_amount_per_year: A reference to the timeseries of the product_amount_per_year taken from
        the product object.
    :ivar bool _calculate_sc: Indicates whether the specific consumption should be calculated or default value should
        be used.


    """

    def __init__(self, product_input: input.ProductInput, product_amount_per_year: pm.Timeseries = None,
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

    def get_scale(self, year, scalar) -> ctn.SC:
        """
        Get the specific consumption value, while also applying a scaling operation.

        :param year: Target year, for which we want to know the specific consumption amount.
        :param scalar: The scalar, scaling the specific consumption.
        :return: The scaled specific consumption.
        """
        sc = self.get(year)
        return ctn.SC(sc.electricity * scalar, sc.heat * scalar, sc.hydrogen * scalar, sc.max_subst_h2)

    def get(self, year) -> ctn.SC:
        """
        Getter for the specific consumption

        :param year: Target year, for which we want to know the specific consumption amount.
        :return: The calculated specific consumption amounts.
        """
        if self._calculate_sc and self.historical_specific_consumption:
            electricity = 0
            heat = 0.0
            for key, value in self.historical_specific_consumption.items():
                prog_amount = value.get_prog(year) / self._product_amount_per_year.get_prog(year)
                electricity += prog_amount * self.efficiency[key].electricity
                heat += prog_amount * self.efficiency[key].heat
            return ctn.SC(electricity, heat, 0, 0)
        else:
            # future TODO: add efficiency to default specific consumption
            return self.default_specific_consumption
