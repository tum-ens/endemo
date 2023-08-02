from __future__ import annotations

import itertools

import endemo2.general.country
import endemo2.general.country_containers
import endemo2.utility.prediction_models
import endemo2.utility.utility_containers
from endemo2.utility import utility as uty
from endemo2.preprocessing import input
from endemo2.utility import prediction_models as pm
from endemo2.general import demand_containers as dc
from endemo2.general import country_containers as cc
from endemo2.preprocessing import preprocessor as pp


class Product:
    """
    Holds all information and objects belonging to a product in the industry of a country.

    :param product_name: The name of the product type. For example "steel_prim".
    :param country_name: The name of the country to whose industry this product belongs to.
    :param population: The countries population amount used to create DataAnalyzer per capita.
    :param gdp: The countries gdp used to create DataAnalyzer per gdp.

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
    :ivar DataStepSequence gdp: A reference to the gdp object of the country.

    :ivar DataAnalyzer _amount_per_year: Used to predict the product amount. The x-axis is time in years.
    :ivar DataAnalyzer _amount_per_gdp: Used to predict the product amount. The x-axis is the countries' gdp.
    :ivar DataAnalyzer _amount_per_capita_per_year: Used to predict the product amount per capita.
        The x-axis is time in years.
    :ivar DataAnalyzer _amount_per_capita_per_gdp: Used to predict the product amount per capita.
        The x-axis is time in years.
    :ivar Coef _amount_country_group_coef: Used to predict the product amount when the product is part of a
        country_group.

    :ivar bool _use_per_capita: Indicates whether the DataAnalyzer that predict amount per capita should be used for
        the forecast.
    :ivar bool _use_gdp_as_x: Indicated whether the DataAnalyzer that use the gdp as x-axis should be used for the
        forecast.
    :ivar bool _empty: Indicates that the product historical data is empty. This is true, if the country is being
        present in the preprocessing table but filters causing the list to be empty.
    :ivar dict[str, float] _nuts2_installed_capacity:
        The installed capacity for this product in each NUTS2 region for the country this product belongs to.
    :ivar bool use_group_coef:
        Indicates whether the coefficient of the group should be used rather than self-calculated one.
    """

    def __init__(self, product_name: str, product_pp: pp.ProductPreprocessed,
                 country_name: str, population: cc.Population, gdp: pm.DataStepSequence):
        self._country_name = country_name
        self._name = product_name
        self._heat_levels = product_pp.heat_levels
        self._perc_used = product_pp.perc_used
        self._nuts2_installed_capacity = product_pp.nuts2_installed_capacity

        # TODO: filter what this class gets through a settings filter

        # TODO: get coefficient for amount (by using the current settings)

        # TODO: create SC object from preprocessed data

    def is_empty(self) -> bool:
        """ Getter for the _empty attribute. """
        return self._empty

    def is_per_capita(self) -> bool:
        """ Getter for the _use_per_capita attribute. """
        return self._use_per_capita

    def is_per_gdp(self) -> bool:
        """ Getter for the _use_gdp_as_x attribute. """
        return self._use_gdp_as_x

    def get_data_regression_obj_amount_per_year(self):
        """ Getter for the _amount_per_year DataAnalyzer. """
        return self._amount_per_year

    def get_data_regression_obj_amount_per_gdp(self):
        """ Getter for the _amount_per_gdp DataAnalyzer. """
        return self._amount_per_gdp

    def get_data_regression_obj_amount_per_capita_per_year(self):
        """ Getter for the _amount_per_capita_per_year DataAnalyzer. """
        return self._amount_per_capita_per_year

    def get_data_regression_obj_amount_per_capita_per_gdp(self):
        """ Getter for the _amount_per_capita_per_gdp DataAnalyzer. """
        return self._amount_per_capita_per_gdp

    def split_heat_levels(self, x: float) -> (float, float, float, float):
        """
        Takes amount of heat as preprocessing and splits it into different heat levels, according to the _heat_levels
        attribute.

        :param float x: The amount of heat to be split into different heat levels.
        :return: The amount of heat in different heat levels as a tuple: (Q1, Q2, Q3, Q4)
        """
        heat = self._heat_levels
        heat.mutable_multiply_scalar(x)

    def calculate_demand(self, year: int) -> dc.Demand:
        """
        Calculates the demand for this product. Returns zero demand when the _empty attribute is true.

        .. math::
            D(y)[TWh/T] = p*A(y)[T]*(c_{electricity}, c_{heat_{split}}, c_{hydrogen})[TWh/T]

        :param year: The target year, the demand should be calculated for.
        :return: The calculated demand.
        """
        if self._empty:
            return dc.Demand()

        sc = self._specific_consumption.get_scale(year, 1 / 3600000)  # get SC and convert from GJ/T to TWH/T
        perc = self._perc_used

        # choose which type of amount based on settings
        amount = self.get_amount_prog(year) * 1000  # convert kT to T

        # calculate demand after all variables are available
        cached_perc_amount = perc * amount
        electricity = cached_perc_amount * sc.electricity
        hydrogen = cached_perc_amount * sc.hydrogen

        heat = self._heat_levels.copy_multiply_scalar(cached_perc_amount * sc.heat)  # separate heat levels

        return dc.Demand(electricity, heat, hydrogen)

    def get_amount_prog(self, year: float) -> float:
        """
        Get the prognosis for the amount of this product in a certain year according to current settings regarding gdp
            and per_capita calculation.

        :param year: The target year, the demand should be projected to.
        :return: The estimated product amount for given year.
        """
        if self._empty:
            return 0.0

        target_x: float
        if self._use_gdp_as_x:
            # if amount prognosis is per gdp, convert year to gdp at that year to get correct prognosis
            target_x = self.gdp.get_prog(year)
        else:
            target_x = year
        active_data_reg_obj = self.get_active_data_regression_obj()
        prog_amount = max(0.0, active_data_reg_obj.get_prog(target_x))
        return prog_amount

    def get_coef(self) -> pm.Coef:
        """ Getter for the coefficients of the currently used DataAnalyzer according to settings. """
        active_data_reg_obj = self.get_active_data_regression_obj()
        return active_data_reg_obj.get_coef()

    def get_active_data_regression_obj(self) -> pm.DataAnalyzer:
        """
        Getter for the current DataAnalyzer object according to current settings regarding gdp
        and per_capita calculation.
        """
        if self._empty:
            return pm.DataAnalyzer([], endemo2.utility.utility_containers.ForecastMethod.LINEAR)
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

    def get_nuts2_installed_capacities(self) -> dict[str, float]:
        """ Getter for the nuts2 installed capacity dictionary. """
        return self._nuts2_installed_capacity


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

    def calculate_demand(self, year: int) -> dc.Demand:
        raise NotImplementedError


class SpecificConsumptionData:
    """
    Holds all consumption data for one product within an industry of a country.

    :param Input input_manager: The preprocessing manager, containing information needed to create this object.
    :param ProductInput product_input: The preprocessing for this specific product type, needed to create it. (Redundant)
    :param DataAnalyzer product_amount_per_year: The DataAnalyzer object from the product to get the predicted product
        amount, used in calculations. (Redundant, but used to prevent circular dependencies)
    :param str country_name: Name of the country, this product belongs to.

    :ivar SC default_specific_consumption: The specific consumption for a product type, that is used as default if
        there is no historical data to predict the specific consumption.
    :ivar dict[DemandType, DataAnalyzer] ts_his_specific_consumption: The dictionary holding DataAnalyzer of different
        demand types for specific consumption.
        Includes different energy carriers with varying efficiencies and is given per product.
    :ivar dict[str, EH] efficiency: Efficiency of each energy carrier in percent in [0,1].
    :ivar DataAnalyzer _product_amount_per_year: A reference to the DataAnalyzer of the product_amount_per_year taken from
        the product object.
    :ivar bool _calculate_sc: Indicates whether the specific consumption should be calculated or default value should
        be used.
    :ivar str county_name: Name of the country the product of this sc belongs to.
    :ivar str product_name: Name of the product this sc belongs to.
    """

    def __init__(self, product_input: input.ProductInput, product_amount_per_year: pm.DataAnalyzer = None,
                 country_name: str = "",
                 input_manager: input.Input = None):

        self.country_name = country_name
        self.product_name = product_input.product_name

        # TODO: get default SC from preprocessor

        # TODO: get timeseries from preprocessor

        # TODO: get historical_sc_available from preprocessor

    def get__calculate_sc(self) -> bool:
        """ Getter for attribute __calculate_sc"""
        return self._calculate_sc

    def _set_to_default_sc(self):
        self._calculate_sc = False

        # 2018 used as a starting point for now. TODO: set a start year in ctrl
        # future TODO: add efficiency to default specific consumption
        self.ts_his_specific_consumption[dc.DemandType.ELECTRICITY] = \
            pm.DataAnalyzer([(2018, self.default_specific_consumption.electricity)],
                            calculation_type=endemo2.utility.utility_containers.ForecastMethod.EXPONENTIAL)
        self.ts_his_specific_consumption[dc.DemandType.HEAT] = \
            pm.DataAnalyzer([(2018, self.default_specific_consumption.heat)],
                            calculation_type=endemo2.utility.utility_containers.ForecastMethod.EXPONENTIAL)
        self.ts_his_specific_consumption[dc.DemandType.HYDROGEN] = \
            pm.DataAnalyzer([(2018, self.default_specific_consumption.hydrogen)],
                            calculation_type=endemo2.utility.utility_containers.ForecastMethod.EXPONENTIAL)

    def get_coef(self, demand_type: dc.DemandType) -> pm.Coef:
        """
        Get the coefficients of the specific consumption DataAnalyzer for a specified demand type.
        :param demand_type: The demand type to get coefficients for. Example: DemandType.ELECTRICITY.
        :return: The coefficients for the demand type.
        """
        return self.ts_his_specific_consumption[demand_type].get_coef()

    def get_scale(self, year, scalar) -> dc.SC:
        """
        Get the specific consumption value, while also applying a scaling operation.

        :param year: Target year, for which we want to know the specific consumption amount.
        :param scalar: The scalar, scaling the specific consumption.
        :return: The scaled specific consumption.
        """
        sc = self.get(year)
        return dc.SC(sc.electricity * scalar, sc.heat * scalar, sc.hydrogen * scalar, sc.max_subst_h2)

    def get_historical_specific_demand(self, demand_type: dc.DemandType) -> [(float, float)]:
        return self.ts_his_specific_consumption[demand_type].get_data()

    def get(self, year) -> dc.SC:
        """
        Getter for the specific consumption

        :param year: Target year, for which we want to know the specific consumption amount.
        :return: The calculated specific consumption amounts.
        """
        electricity = self.ts_his_specific_consumption[dc.DemandType.ELECTRICITY].get_prog(year)
        heat = self.ts_his_specific_consumption[dc.DemandType.HEAT].get_prog(year)
        hydrogen = self.ts_his_specific_consumption[dc.DemandType.HYDROGEN].get_prog(year)
        return dc.SC(max(0.0, electricity), max(0.0, heat), max(0.0, hydrogen), 0.0)
