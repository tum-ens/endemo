"""
This module contains all classes directly representing in data series and prognosis calculations.
"""

from __future__ import annotations

import warnings
from typing import Any, Union

import statistics as st

import numpy as np

from endemo2.data_structures.containers import Interval, Datapoint
from endemo2.data_structures.enumerations import ForecastMethod
from endemo2 import utility as uty
from endemo2.data_structures import containers as ctn


class Coef:
    """
    The container for the coefficients of different forecast methods.

    :ivar (Datapoint, r) _exp:
        (x0, y0) is the start point for the exponential calculation and r is the growth rate.
        Used for calculation y(x) = y0 * (1+r)^(x - x0)
    :ivar (k0, k1) _lin: Used for the calculation f(x) = k0 + k1 * x
    :ivar (k0, k1, k2) _quadr: Used for the calculation f(x) = k0 + k1 * x + k2 * x^2
    :ivar float _offset: Additional constant offset.
    :ivar ForecastMethod _method: Method used for calculating output.
    :ivar bool _fixed_forecast_method: indicates that the method should not be changed anymore for this coefficient
        object. Example: Is used when setting the exponential forecast method for timeseries with only one data point.
    """
    def __init__(self):
        self._exp: (Datapoint, float) = None
        self._log: (float, float) = None
        self._lin: (float, float) = None
        self._quadr: (float, float, float) = None
        self._offset: Union[float, None] = None
        self._method: Union[ForecastMethod, None] = None
        self._fixed_forecast_method: bool = False

    def get_method(self) -> ForecastMethod:
        """ Getter for the forecast method attribute. """
        return self._method

    def set_method(self, method: ForecastMethod, fixate=False):
        """
        Setter for the forecast method.

        :param method: The method that should be used from now on.
        :param fixate: If True, makes sure that method cannot be reset for this coefficient object.
        """
        if not self._fixed_forecast_method:
            self._method = method
        if fixate:
            self._fixed_forecast_method = fixate

    def set_exp_start_point(self, start_point: Datapoint):
        """
        Setter for the exponential start point.

        :param start_point: The new start point for the exponential forecast method.
        """
        if self._exp is not None:
            prior_growth_rate = self._exp[1]
            self._exp = (start_point, prior_growth_rate)
        if self._exp is None:
            self._exp = (start_point, 0.0)

    def set_exp_growth_rate(self, exp_growth_rate: float):
        """
        Setter for the exponential growth rate.

        :param exp_growth_rate: The new growth rate for the exponential forecast method.
        """
        if self._exp is not None:
            prior_start_point = self._exp[0]
            self._exp = (prior_start_point, exp_growth_rate)
        if self._exp is None:
            self._exp = (None, exp_growth_rate)

    def set_exp(self, start_point: Datapoint, exp_growth_rate: float):
        """
        Setter for the exponential coefficients.

        :param start_point: The new start point for the exponential forecast method.
        :param exp_growth_rate: The new growth rate for the exponential forecast method.
        """
        self._exp = (start_point, exp_growth_rate)

    def set_log(self, k0: float, k1: float):
        """
        Setter for the logarithmic coefficients.

        :param k0: The constant coefficient.
        :param k1: The logarithmic coefficient.
        """
        self._log = (k0, k1)

    def set_lin(self, k0: float, k1: float):
        """
        Setter for the linear coefficients.

        :param k0: The constant coefficient.
        :param k1: The linear coefficient.
        """
        self._lin = (k0, k1)

    def set_quadr(self, k0: float, k1: float, k2: float):
        """
        Setter for the quadratic coefficients.

        :param k0: The constant coefficient.
        :param k1: The linear coefficient.
        :param k2: The quadratic coefficient.
        """
        self._quadr = (k0, k1, k2)

    def set_offset(self, k0: float):
        """
        Setter for the additional offset.

        :param k0: The additional constant offset.
        """
        self._offset = k0

    def get_exp_y(self, target_x) -> Union[float, None]:
        """
        Returns the y-axis value of the function at the given x according to the exponential method.

        :param target_x: The x_axis value the function should be applied on.
        :return: The according y-axis value if exponential start point and growth rate is set, otherwise None.
        """
        if self._exp is not None and self._exp[0] is not None:
            return uty.exp_change(self._exp[0], self._exp[1], target_x)
        else:
            return None

    def get_log_y(self, target_x) -> Union[float, None]:
        """
        Returns the y-axis value of the function at the given x according to the logarithmic method.

        :param target_x: The x_axis value the function should be applied on.
        :return: The according y-axis value if the logarithmic coefficients are set, otherwise None.
        """
        if self._log is not None:
            return uty.log_prediction(self._log, target_x)
        else:
            return None

    def get_lin_y(self, target_x) -> Union[float, None]:
        """
        Returns the y-axis value of the function at the given x according to the linear method.

        :param target_x: The x_axis value the function should be applied on.
        :return: The according y-axis value if the linear coefficients are set, otherwise None.
        """
        if self._lin is not None:
            return uty.lin_prediction(self._lin, target_x)
        else:
            return None

    def get_quadr_y(self, target_x) -> Union[float, None]:
        """
        Returns the y-axis value of the function at the given x according to the quadratic method.

        :param target_x: The x_axis value the function should be applied on.
        :return: The according y-axis value if the quadratic coefficients are set, otherwise None.
        """
        if self._quadr is not None:
            return uty.quadr_prediction(self._quadr, target_x)
        else:
            return None

    def get_quadr_offset_y(self, target_x) -> Union[float, None]:
        """
        Returns the y-axis value of the function at the given x according to the quadratic offset method.

        :param target_x: The x_axis value the function should be applied on.
        :return: The according y-axis value if the quadratic coefficients and offset are set, otherwise None.
        """
        if self._offset is not None and self._quadr is not None:
            quadr_offset = (self._quadr[0] + self._offset, self._quadr[1], self._quadr[2])
            return uty.quadr_prediction(quadr_offset, target_x)
        else:
            return None

    def get_function_y(self, target_x) -> Union[float, None]:
        """
        Returns the y-axis value of the function at the given x according to the used method.

        :param target_x: The x_axis value the function should be applied on.
        :return: The according y-axis value if everything of the chosen method (and the method) is set, otherwise None.
        """
        match self._method:
            case ForecastMethod.LINEAR:
                return self.get_lin_y(target_x)
            case ForecastMethod.QUADRATIC:
                return self.get_quadr_y(target_x)
            case ForecastMethod.EXPONENTIAL:
                return self.get_exp_y(target_x)
            case ForecastMethod.QUADRATIC_OFFSET:
                return self.get_quadr_offset_y(target_x)
            case ForecastMethod.LOGARITHMIC:
                return self.get_log_y(target_x)
            case None:
                warnings.warn("No forecast method selected for coefficients.")
                return None

    def get_log(self) -> (float, float):
        """
        Getter for the logarithmic coefficient.

        :return: The logarithmic coefficient of form (k0, k1).
        """
        return self._log

    def get_lin(self) -> (float, float):
        """
        Getter for the linear coefficient.

        :return: The linear coefficient of form (k0, k1).
        """
        return self._lin

    def get_quadr(self) -> (float, float, float):
        """
        Getter for the quadratic coefficient.

        :return: The quadratic coefficient of form (k0, k1, k2).
        """
        return self._quadr

    def get_exp(self) -> (Datapoint, float):
        """
        Getter for the exponential coefficient.

        :return: The exponential execution variables of form ((start_x, start_y), growth_rate)
        """
        return self._exp

    def get_offset(self) -> float:
        """
        Getter for the additional offset.

        :return: The additional offset
        """
        return self._offset


class RigidTimeseries:
    """
    Class representing data that should be taken just like it is. Without interpolation, without coefficients,
    only the data over time.

    :param data: The timeseries data, where the x-axis is Time and the y-axis is some value over time.
        Can contain NaN and Inf values.

    :ivar [Datapoint] _data: The timeseries data, where the x-axis is Time and the y-axis is some value over time.
        Filtered to not contain any NaN or Inf values.
    """

    def __init__(self, data: [Datapoint]):
        # clean data before saving; also copies the input_and_settings data
        self._data = uty.filter_out_nan_and_inf(data)

    def __str__(self):
        return str(self._data)

    def get_last_available_data_entry_or_zero(self) -> Datapoint:
        """ Returns the last data entry in the timeseries data if present, else 0.0. """
        if len(self._data) == 0:
            return Datapoint(0.0)
        else:
            return self._data[-1]

    def get_value_at_year(self, year: int) -> float:
        """
        Returns the value of the RigidTimeseries at the given year, if present. If the value is not present, throws an
        error.

        :param year: The year the value should be taken from.
        :return: The value of the timeseries at year.
        """
        res = [y for (x, y) in self._data if x == year]

        if len(res) == 0:
            raise ValueError("Trying to access value in RigidTimeseries at a year, where no value is present.")
        else:
            return res[0]


class TwoDseries:
    """
    A class representing a data series [(x, y)]. Both axis can be any type of data.

    :param [Datapoint] data: The TwoDseries data, where the x-axis and the y-axis can be any floating point values.
        Can contain NaN and Inf values.

    :ivar [Datapoint] _data: Where the x-axis is first in tuple and the y-axis is second.
    :ivar Coef coefficients: The coefficients for this data series.
    """

    def __init__(self, data: [Datapoint]):
        # clean data before saving; also copies the input_and_settings data
        self._data = uty.filter_out_nan_and_inf(data)
        self.coefficients = None

    def __str__(self):
        return str(self._data)

    def generate_coef(self) -> Coef:
        """
        Generate and save the coefficients of all regression methods.

        :return: The generated Coefficient object.
        """
        self.coefficients = uty.apply_all_regressions(self._data)

        if len(self._data) == 1:
            self.coefficients.set_exp_start_point(self._data[0])
            self.coefficients.set_method(ForecastMethod.EXPONENTIAL, fixate=True)

        return self.coefficients

    def get_coef(self) -> Coef:
        """
        Safely get the coefficients. If they were not generated before, generates them.

        :return: The resulting coefficient object.
        """
        if self.coefficients is None:
            return self.generate_coef()
        else:
            return self.coefficients

    def is_empty(self) -> bool:
        """
        Indicates whether there is no data present.

        :return: True if data is empty, False otherwise.
        """
        return len(self._data) == 0

    def is_zero(self) -> bool:
        """
        Indicates whether the data on the y-axis has only zeroes.

        :return: True if data's y-axis only contains zeros, False otherwise.
        """
        return uty.is_tuple_list_zero(self._data)

    def get_data(self) -> [Datapoint]:
        """ Getter for the data attribute. """
        return self._data

    def get_mean_y(self) -> float:
        """
        Get mean of all values on the y-axis of the data.

        :return: The mean of all y values of the data.
        """
        only_y = [y for (x, y) in self._data]
        return st.mean(only_y)

    def append_others_data(self, other_tds: TwoDseries) -> TwoDseries:
        """
        Append all data of another timeseries to self and return self.

        :param other_tds: The TwoDseries, whose data should be appended.
        :return: self
        """
        self._data += other_tds._data
        return self


class Timeseries(TwoDseries, RigidTimeseries):
    """
    A class strictly representing a value over time. This usage is a class invariant and the class should not be used
    in any other way.

    :param [Datapoint] data: The timeseries data, where the x-axis is Time and the y-axis is some value over time.
        Can contain NaN and Inf values.

    :ivar [Datapoint] _data: Where the x-axis is Time and the y-axis is some value over time.
    """

    def __init__(self, data: [Datapoint]):
        super().__init__(data)

    @classmethod
    def merge_two_timeseries(cls, t1: Timeseries, t2: Timeseries) -> TwoDseries:
        """
        Merge the two Timeseries on the condition that the year is the same.
        Note: The result is not a Timeseries!

        :param t1: Timeseries to zip t1 [(a,b)]
        :param t2: Timeseries to zip t2 [(c, d)]
        :return: The zipped TwoDseries in format [(b, d)] for where a == c.
        """
        d1 = t1._data
        d2 = t2._data
        return TwoDseries(uty.zip_data_on_x(d1, d2))

    @classmethod
    def map_two_timeseries(cls, t1: Timeseries, t2: Timeseries, function) -> Any:
        """
        Map the two Timeseries according to the given function.

        :param t1: Timeseries to zip t1 [(x, y1)]
        :param t2: Timeseries to zip t2 [(x, y2)]
        :param function: The function that is applied. Should be of form lambda x y1 y2 -> ...
        :return: The result of the applied function.
        """
        d1 = t1._data
        d2 = t2._data
        return TwoDseries(uty.zip_data_on_x_and_map(d1, d2, function))

    @classmethod
    def map_y(cls, t: Timeseries, function) -> Timeseries:
        """
        Map the y-axis of the Timeseries and return a newly created timeseries as a result.

        :param t: The timeseries to map.
        :param function: The mapping function of the form lambda x -> ...
        :return: A copy-mapped timeseries.
        """
        return Timeseries(uty.map_data_y(t._data, function))

    def append_others_data(self, other_ts: Timeseries) -> Timeseries:
        """
        Append all data of another timeseries to self and return self.
        Timeseries also sorts the result, so it can remain a valid timeseries.

        :param other_ts: The timeseries, whose data should be appended.
        :return: self
        """
        super().append_others_data(other_ts)
        self._data.sort(key=lambda data_point: data_point.x)
        return self

    def add(self, other_ts: Timeseries) -> Timeseries:
        """
        Add the data of the other_ts to self. Also return a reference to self.
        When a datapoint is only present in one of the timeseries it is added!

        :param other_ts: The timeseries, whose data should be added to self.
        :return: A reference to self.
        """
        (start, end) = uty.get_series_range([self, other_ts])
        other_ts = Timeseries.fill_empty_years_with_value(other_ts, Interval(start, end), np.NaN)
        self.fill_own_empty_years_with_value(Interval(start, end), np.NaN)

        zipped = list(zip(other_ts._data, self._data))
        added_data = []
        for (x, y1), (_, y2) in zipped:
            if y1 is np.NaN and y2 is np.NaN:
                continue
            y1_nan_to_zero = 0.0 if y1 is np.NaN else y1
            y2_nan_to_zero = 0.0 if y2 is np.NaN else y2
            added_data.append(Datapoint(x, y1_nan_to_zero + y2_nan_to_zero))

        self._data = added_data
        return self

    def divide_by(self, other_ts: Timeseries) -> Timeseries:
        """
        Divide the data of self by the data of other_ts. Also return a reference to self.

        :param other_ts: The timeseries, whose data should be divided by.
        :return: A reference to self.
        """
        others_data_without_zeros = [Datapoint(x, y) for (x, y) in other_ts._data if y != 0]
        self._data = uty.zip_data_on_x_and_map(self._data, others_data_without_zeros,
                                               lambda x, y1, y2: Datapoint(x, y1 / y2))
        return self

    def scale(self, scalar: float) -> Timeseries:
        """
        Scale own data by scalar. Also return a reference to self.

        :param scalar: The scalar that should be scaled by.
        :return: A reference to self.
        """
        self._data = [Datapoint(x, y * scalar) for (x, y) in self._data]
        return self

    def get_last_data_entry(self) -> Datapoint:
        """
        Getter for the last available entry in data.

        :return: The last entry, or a string if data is empty.
        """
        if self.is_empty():
            return "", ""
        else:
            return self._data[-1]

    def get_value_at_year(self, year: int) -> float:
        """
        Returns the value of the RigidTimeseries at the given year, if present. If the value is not present, throws an
        error.

        :param year: The year, the data should be taken from.
        :return: The value of the timeseries at year.
        """
        res = [y for (x, y) in self._data if x == year]

        if len(res) == 0:
            raise ValueError("Trying to access value in RigidTimeseries at a year, where no value is present.")
        else:
            return res[0]

    def get_value_at_year_else_zero(self, year: int) -> float:
        """
        Returns the value of the RigidTimeseries at the given year, if present. If the value is not present, returns
        zero.

        :param year: The year, the data should be taken from.
        :return: The value of the timeseries at year, or zero if no data is present.
        """
        res = [y for (x, y) in self._data if x == year]

        if len(res) == 0:
            return 0.0
        else:
            return res[0]

    def fill_own_empty_years_with_value(self, interval: Interval, fill_value: float):
        """
        Fill own data in interval with fill value

        :param interval: The interval that should be filled.
        :param fill_value: The value that should be used to fill gaps
        """
        result = []
        current_year = interval.start
        for year, value in self._data:
            # add zeros before the next year that is in timeseries to fill gaps
            while current_year < year:
                result.append(Datapoint(current_year, fill_value))
                current_year += 1
            result.append(Datapoint(year, value))
            current_year += 1

        while current_year <= interval.end:
            result.append(Datapoint(current_year, fill_value))
            current_year += 1

        self._data = result

    @classmethod
    def fill_empty_years_with_value(cls, ts: Timeseries, interval: Interval, fill_value: float) -> Timeseries:
        """
        Create a timeseries that has data for each year in interval. Take value from given timeseries if present, else
        fill with given value.

        :param ts: The given timeseries, which values are copied.
        :param interval: The interval in which data has to be present for every year.
        :param fill_value: Value with which gaps in the data should be filled.
        :return: The created timeseries with values from ts and filled gaps with given value.
        """
        result = Timeseries(ts._data.copy())
        result.fill_own_empty_years_with_value(interval, fill_value)

        return result


class IntervalForecast:
    """
    The class depicting a given exponential prediction with different growth rates in certain intervals.

    :param list[(Interval, float)] progression_data: The input_and_settings progression data given as a list of
        intervals and their corresponding growth rate. For example [(Interval(start, end), percentage_growth)].

    :ivar list[(Interval, float)] _interval_changeRate: The same as progression_data, just the growth rate is not in
        percentage anymore, but percentage/100
    """

    def __init__(self, progression_data: list[(Interval, float)]):
        # map percentage to its hundredth
        self._interval_changeRate = [(prog[0], prog[1] / 100) for prog in progression_data]

    def get_forecast(self, target_x: float, start_point: Datapoint) -> float:
        """
        Get the prognosis of the y-axis value for a target x-axis value from the manual exponential
        interval-growth-rate forecast.

        .. math::
            y=s_x*(1+r_{1})^{(intvl^{(1)}_{b}-s_y)}*(1+r_{2})^{(intvl^{(2)}_{b}-intvl^{(2)}_{a})}*\\text{...}*(1+r_{3})^
            {(x-intvl^{(3)}_{a})}

        :param start_point: The (x, y) Tuple, that is used as the first value for the exponential growth.
        :param target_x: The target x-axis value.
        :return: The predicted y value at x-axis value x.
        """
        result = start_point.y
        for interval_change in self._interval_changeRate:
            start = max(start_point.x, interval_change[0].start)  # cut off protruding years at start
            end = min(target_x, interval_change[0].end)  # cut off protruding years at end
            exp = max(0, end - start)  # clamp to 0, to ignore certain intervals
            result *= (1 + interval_change[1]) ** exp

        return result

