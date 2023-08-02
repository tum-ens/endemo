from __future__ import annotations

import enum
import warnings
from typing import Any

import numpy as np
import statistics as st

from endemo2.utility import utility as uty
from endemo2.general import demand_containers as ctn
from endemo2.utility.utility_containers import ForecastMethod


class Coef:
    """
    The container for the coefficients of different forecast methods.

    :ivar ((x0, y0), r) _exp:
        (x0, y0) is the start point for the exponential calculation and r is the growth rate.
        Used for calculation y(x) = y0 * (1+r)^(x - x0)
    :ivar (k0, k1) _lin: Used for the calculation f(x) = k0 + k1 * x
    :ivar (k0, k1, k2) _quadr: Used for the calculation f(x) = k0 + k1 * x + k2 * x^2
    :ivar float _offset: Additional constant offset.
    :ivar ForecastMethod _method: Method used for calculating output.
    """
    def __init__(self,
                 exp_start_point_xy: (float, float) = (0.0, 0.0), exp_growth_rate: float = 0.0,
                 lin: (float, float) = (0.0, 0.0),
                 quadr: (float, float, float) = (0.0, 0.0, 0.0),
                 offset: float = 0.0,
                 method: ForecastMethod = None):
        self._exp = ((exp_start_point_xy[0], exp_start_point_xy[1]), exp_growth_rate)
        self._lin = (lin[0], lin[1])
        self._quadr = (quadr[0], quadr[1], quadr[2])
        self._offset = offset
        self._method = method

    def set_method(self, method: ForecastMethod):
        """ Setter for the forecast method. """
        self._method = method

    def set_exp(self, start_point: (float, float), exp_growth_rate: float):
        """ Setter for the exponential coefficients. """
        self._exp = (start_point, exp_growth_rate)

    def set_lin(self, k0: float, k1: float):
        """ Setter for the linear coefficients. """
        self._lin = (k0, k1)

    def set_quadr(self, k0: float, k1: float, k2: float):
        """ Setter for the quadratic coefficients. """
        self._quadr = (k0, k1, k2)

    def set_offset(self, k0: float, k1: float, k2: float):
        """ Setter for the quadratic coefficients. """
        self._quadr = (k0, k1, k2)

    def get_exp_y(self, target_x) -> float:
        """ Returns the y-axis value of the function at the given x according to the exponential method. """
        return uty.exp_change((self._exp[0][0], self._exp[0][1]), self._exp[1], target_x)

    def get_lin_y(self, target_x) -> float:
        """ Returns the y-axis value of the function at the given x according to the linear method. """
        return uty.lin_prediction(self._lin, target_x)

    def get_quadr_y(self, target_x) -> float:
        """ Returns the y-axis value of the function at the given x according to the quadratic method. """
        return uty.quadr_prediction(self._quadr, target_x)

    def get_quadr_offset_y(self, target_x) -> float:
        """ Returns the y-axis value of the function at the given x according to the quadratic offset method. """
        quadr_offset = (self._quadr[0] + self._offset, self._quadr[1], self._quadr[2])
        return uty.quadr_prediction(quadr_offset, target_x)

    def get_function_y(self, target_x) -> float:
        """ Returns the y-axis value of the function at the given x according to the used method. """
        match self._method:
            case ForecastMethod.LINEAR:
                return self.get_lin_y(target_x)
            case ForecastMethod.QUADRATIC:
                return self.get_quadr_y(target_x)
            case ForecastMethod.EXPONENTIAL:
                return self.get_exp_y(target_x)
            case ForecastMethod.QUADRATIC_OFFSET:
                return self.get_quadr_offset_y(target_x)
            case None:
                warnings.warn("No forecast method selected for coefficients.")


class StartPoint(enum.Enum):
    """ Denotes the type of start points used for the exponential forecast method. """
    LAST_AVAILABLE = 0
    AVERAGE_VALUE = 1
    MANUAL = 2


class RigidTimeseries:
    """
    Class representing data that should be taken just like it is. Without interpolation, without coefficients,
    only the data over time.

    :ivar [(float, float)] _data: Where the x-axis is Time and the y-axis is some value over time.
    """

    def __init__(self, data: [(float, float)]):
        # clean data before saving; also copies the input data
        self._data = uty.filter_out_nan_and_inf(data)

    def get_value_at_year(self, year: int):
        res = [y for (x, y) in self._data if x == year]

        if len(res) == 0:
            raise ValueError("Trying to access value in RigidTimeseries at a year, where no value is present.")
        else:
            return res[0]


class TwoDseries:
    """
    A class representing a data series [(x, y)]. Both axis can be any type of data.

    :ivar [(float, float)] _data: Where the x-axis is first in tuple and the y-axis is second.
    :ivar Coef coefficients: The coefficients for this data series.
    """

    def __init__(self, data: [(float, float)]):
        # clean data before saving; also copies the input data
        self._data = uty.filter_out_nan_and_inf(data)
        self.coefficients = None

    def generate_coef(self) -> Coef:
        self.coefficients = uty.apply_all_regressions(self._data)
        return self.coefficients

    def get_coef(self) -> Coef:
        if self.coefficients is None:
            return self.generate_coef()
        else:
            return self.coefficients

    def is_empty(self) -> bool:
        return len(self._data) == 0

    def get_data(self):
        return self._data


class Timeseries(TwoDseries):
    """
    A class strictly representing a value over time. This usage is a class invariant and the class should not be used
    in any other way.

    :ivar [(float, float)] _data: Where the x-axis is Time and the y-axis is some value over time.
    """

    def __init__(self, data: [(float, float)]):
        super().__init__(data)

    @classmethod
    def merge_two_timeseries(cls, t1: Timeseries, t2: Timeseries) -> TwoDseries:
        d1 = t1._data
        d2 = t2._data
        return TwoDseries(uty.zip_data_on_x(d1, d2))

    @classmethod
    def map_two_timeseries(cls, t1: Timeseries, t2: Timeseries, function) -> Any:
        d1 = t1._data
        d2 = t2._data
        return TwoDseries(uty.zip_data_on_x_and_map(d1, d2, function))

    @classmethod
    def map_y(cls, t: Timeseries, function) -> Timeseries:
        return Timeseries(uty.map_data_y(t._data, function))

    def add(self, other_ts: Timeseries) -> Timeseries:
        self._data = uty.zip_data_on_x_and_map(self._data, other_ts._data,
                                               lambda x, y1, y2: (x, y1 + y2))
        return self

    def divide_by(self, other_ts: Timeseries) -> Timeseries:
        others_data_without_zeros = [(x, y) for (x, y) in other_ts._data if y != 0]
        self._data = uty.zip_data_on_x_and_map(self._data, others_data_without_zeros,
                                               lambda x, y1, y2: (x, y1 / y2))
        return self

    def scale(self, scalar: float) -> Timeseries:
        self._data = [(x, y * scalar) for (x, y) in self._data]
        return self

    def is_empty(self) -> bool:
        return len(self._data) == 0

    def is_zero(self) -> bool:
        return uty.is_tuple_list_zero(self._data)


class DataAnalyzer:
    """
    A DataAnalyzer holds information about a process' values from the past and provides projections into the future.

    :param data: The historical data given for this DataAnalyzer.
    :param calculation_type: The forecast method, that should be used.
    :param rate_of_change: The manually given rate of change for the exponential forecast method.

    :ivar [(float, float)] _data: The historical data for this DataAnalyzer.
    :ivar Coef _coef: All the coefficients for different forecast methods contained in an object that provides
        functions for them.
    :ivar ForecastMethod _calculation_type: The currently selected forecast method that should be used for projections.
    """

    def __init__(self, data: [(float, float)], calculation_type: ForecastMethod, rate_of_change=0.0):
        self._data = data

        if len(self._data) < 2:
            # with only one value available, no regression possible
            self._calculation_type = ForecastMethod.EXPONENTIAL
        elif len(self._data) < 3 and calculation_type is not ForecastMethod.EXPONENTIAL:
            # quadratic regression only possible with > 2 data points
            self._calculation_type = ForecastMethod.LINEAR
        else:
            self._calculation_type = calculation_type

        # calculate all coefficients
        self._coef = Coef(method=self._calculation_type)
        self._set_coef_exp(rate_of_change, StartPoint.LAST_AVAILABLE)
        self._calc_coef_lin()
        self._calc_coef_quadr()

    def get_value(self, target_x):
        """
        Get the y-axis value for a certain target_x.
        Combines historical data and prediction data. When historical data is available it is used.
        When not, a prognosis is made instead.

        :param target_x: The target x-axis value.
        :return: The corresponding y-axis value, historical or prognosis.
        """

        last_year = self.get_last_data_entry()[1]

        if target_x <= last_year:
            for (x, y) in self.get_data():
                if target_x == x:
                    return y
                    # if target year not in data (spotty data or in future) use prediction instead
        return self.get_prog(target_x)

    def get_prog(self, x) -> float:
        """
        Getter for the prognosis of this DataAnalyzer.

        :param x: The x-axis value. Example: target year for projection into the future.
        :return: The estimated y-axis value for the target x.
        """
        return self._coef.get_function_y(x)

    def _set_coef_exp(self, rate_of_change: float, start_point: StartPoint, manual: (float, float) = (0, 0)):
        """
        Calculates and sets the coefficient for the exponential forecast method f(x) = y0 * (1 + r)^(x - x0).

        :param float rate_of_change: The rate of change r.
        :param StartPoint start_point: The type of start point that should be used.
        :param (float, float) manual: Optional: A manual startpoint (x0, y0).
        :todo: implement manual startpoint in excel sheets
        """
        (start_x, start_y) = (0, 0)
        match start_point:
            case StartPoint.LAST_AVAILABLE:
                if len(self._data) <= 0:
                    (start_x, start_y) = (np.NaN, np.NaN)
                else:
                    (start_x, start_y) = self._data[-1]
            case StartPoint.AVERAGE_VALUE:
                (split_x, split_y) = zip(*self._data)
                start_x = st.mean(split_x)
                start_y = st.mean(split_y)
            case StartPoint.MANUAL:
                (start_x, start_y) = manual

        self._coef.set_exp(start_point=(start_x, start_y), exp_growth_rate=rate_of_change)

    def get_mean_y(self) -> float:
        """
        Get mean of all values on the y-axis of the data.
        :return: The mean of all y values of the data.
        """
        only_y = [y for (x, y) in self._data]
        return st.mean(only_y)

    def _calc_coef_lin(self):
        """ Calculates and sets the coefficient for the linear forecast method. """
        if len(self._data) < 2:
            if len(self._data) == 0:
                self._coef.set_lin(0, 0)
            else:
                self._coef.set_lin(self._data[0][1], 0)
            return
        lin_coef = uty.linear_regression(self._data)
        self._coef.set_lin(lin_coef[0], lin_coef[1])

    def _calc_coef_quadr(self):
        """ Calculates and sets the coefficient for the quadratic forecast method. """
        if len(self._data) < 3:
            if len(self._data) == 0:
                self._coef.set_quadr(0, 0, 0)
            else:
                self._coef.set_quadr(self._data[0][1], 0, 0)
            return
        quadr_coef = uty.quadratic_regression(self._data)
        self._coef.set_quadr(quadr_coef[0], quadr_coef[1], quadr_coef[2])

    def get_coef(self) -> Coef:
        """ Getter for the coefficient container. """
        return self._coef

    def get_data(self) -> list[(float, float)]:
        """ Getter for the historical data. """
        return self._data

    def get_last_data_entry(self) -> (float, float):
        """ Getter for the last available entry in historical data. """
        if len(self._data) <= 0:
            return "-", "-"
        else:
            return self._data[-1]

    def get_prog_exp(self, x) -> float:
        """
        Get the prognosis of the y-axis value for a target x-axis value with the exponential forecast method.

        :param x: The target x-axis value.
        :return: The predicted y value at x-axis value x.
        """
        return self._coef.get_exp_y(x)

    def get_prog_lin(self, x) -> float:
        """
        Get the prognosis of the y-axis value for a target x-axis value with the linear forecast method.

        :param x: The target x-axis value.
        :return: The predicted y value at x-axis value x.
        """
        return self._coef.get_lin_y(x)

    def get_prog_quadr(self, x) -> float:
        """
        Get the prognosis of the y-axis value for a target x-axis value with the quadratic forecast method.

        :param x: The target x-axis value.
        :return: The predicted y value at x-axis value x.
        """
        return self._coef.get_quadr_y(x)


class DataManualPrediction(DataAnalyzer):
    """
    A variant of the DataAnalyzer class, where there is a manual forecast available that is read from the preprocessing and
    used for the forecast.

    :param [(float, float)] historical_data: The historical data. Passed onto parent class.
    :param [(float, float)] prediction_data: The manual prediction data. This is saved and used for the forecast.
    :param ForecastMethod calculation_type: The forecast type, should the parent class be used instead. Is passed on to
        the parent class.
    :param float rate_of_change: The rate of change for the exponential forecast method, should this one be selected
        for use in the parent class.

    :ivar [(float, float)] _prediction: The manual prediction, which is used for the forecast.
    """
    def __init__(self, historical_data: [(float, float)], prediction_data: [(float, float)],
                 calculation_type: ForecastMethod = ForecastMethod.LINEAR, rate_of_change=0.0):
        super().__init__(historical_data, calculation_type, rate_of_change)
        self._prediction = prediction_data

    def get_value(self, target_x):
        """
        Get the y-axis value for a certain target_x.
        Combines historical data and prediction data. When historical data is available it is used.
        When not, a prognosis is made instead.

        :param target_x: The target x-axis value.
        :return: The corresponding y-axis value, historical or prognosis.
        """

        last_year = self.get_last_data_entry()[1]

        if target_x <= last_year:
            for (x, y) in self.get_data():
                if target_x == x:
                    return y
        # if target year not in data (spotty data or in future) use prediction instead
        return self.get_manual_prog(target_x)

    def get_prog(self, target_x) -> float:
        """
        Get the prognosis of the y-axis value by the standard method for this class.

        :param target_x: The target x-axis value.
        :return: The predicted y value at x-axis value x.
        """
        return self.get_manual_prog(target_x)

    def get_manual_prog(self, target_x: float):
        """
        Get the prognosis of the y-axis value for a target x-axis value from the manual forecast.

        :param target_x: The target x-axis value.
        :return: The predicted y value at x-axis value x.
        """
        return [y for (x, y) in self._prediction if x == target_x][0]

    def get_prediction_raw(self) -> [(float, float)]:
        """ Getter for the manual prediction data. """
        return self._prediction


class IntervalForecast:
    """
    The class depicting a given exponential prediction with different growth rates in certain intervals.

    :param [(ctn.Interval, float)] progression_data: The input progression data given as a list of intervals and their
        corresponding growth rate. For example [(Interval(start, end), percentage_growth)].

    :ivar [(ctn.Interval, float)] _interval_changeRate: The same as progression_data, just the growth rate is not in
        percentage anymore, but percentage/100
    """

    def __init__(self, progression_data: [(ctn.Interval, float)]):
        # map percentage to its hundredth
        self._interval_changeRate = [(prog[0], prog[1] / 100) for prog in progression_data]

    def get_forecast(self, target_x: float, start_point: (float, float)):
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
        if target_x <= start_point[0]:
            # take gdp from historical data
            for (a1, a2), (b1, b2) in zip(self._data[:-1], self._data[1:]):
                if a1 == target_x or target_x < a1:
                    return a2
                elif b1 == target_x:
                    return b2
                elif a1 < target_x < b1:
                    # a gap in historical data => use the closest year
                    if target_x - a1 <= b1 - target_x:
                        return a2
                    else:
                        return b2

        # calculate result in future
        result = start_point[1]
        for interval_change in self._interval_changeRate:
            start = max(start_point[0], interval_change[0].start)  # cut off protruding years at start
            end = min(target_x, interval_change[0].end)  # cut off protruding years at end
            exp = max(0, end - start)  # clamp to 0, to ignore certain intervals
            result *= (1 + interval_change[1]) ** exp

        return result

class DataStepSequence(DataAnalyzer):
    """
    A variant of the DataAnalyzer class, where there is a forecast given in the shape of intervals with an exponential
    growth rate.

    :param [(float, float)] historical_data: The historical data. Passed onto parent class.
    :param [(Interval, float)] progression_data: The manual progression data in form of an x-axis interval in
        combination with the exponential growth rate.
    :param ForecastMethod calculation_type: The forecast type, should the parent class be used instead. Is passed on to
        the parent class.
    :param float rate_of_change: The rate of change for the exponential forecast method of the parent class, should
        the parent class be used for calculation and this method be selected.

    :ivar (float, float) _his_end_value: The last value of historical data used as a starting point for the exponential
        interval calculation.
    :ivar [(Interval, float)] _interval_changeRate: The Interval-Change-Rate pairings that are used by the forecast
        calculation for this class.
    """

    def __init__(self, historical_data: [(float, float)], progression_data: [(ctn.Interval, float)],
                 calculation_type: ForecastMethod = ForecastMethod.LINEAR,
                 rate_of_change=0.0):
        super().__init__(historical_data, calculation_type, rate_of_change)

        # determine start value
        self._his_end_value = self._data[-1]

        # cut out unnecessary progression
        self._interval_changeRate = [progression_point for progression_point in progression_data
                                     if progression_point[0].end > self._his_end_value[0]]

        # map percentage to its hundredth
        self._interval_changeRate = [(prog[0], prog[1] / 100) for prog in self._interval_changeRate]

    def get_prog(self, target_x) -> float:
        """
        Get the prognosis of the y-axis value by the standard method for this class.

        :param target_x: The target x-axis value.
        :return: The predicted y value at x-axis value x.
        """
        return self.get_manual_prog(target_x)

    def get_manual_prog(self, target_x: float):
        """
        Get the prognosis of the y-axis value for a target x-axis value from the manual exponential
        interval-growth-rate forecast.

        .. math::
            y=s_x*(1+r_{1})^{(intvl^{(1)}_{b}-s_y)}*(1+r_{2})^{(intvl^{(2)}_{b}-intvl^{(2)}_{a})}*\\text{...}*(1+r_{3})^
            {(x-intvl^{(3)}_{a})}

        :param target_x: The target x-axis value.
        :return: The predicted y value at x-axis value x.
        """
        if target_x <= self._his_end_value[0]:
            # take gdp from historical data
            for (a1, a2), (b1, b2) in zip(self._data[:-1], self._data[1:]):
                if a1 == target_x or target_x < a1:
                    return a2
                elif b1 == target_x:
                    return b2
                elif a1 < target_x < b1:
                    # a gap in historical data => use the closest year
                    if target_x - a1 <= b1 - target_x:
                        return a2
                    else:
                        return b2

        # calculate result in future
        result = self._his_end_value[1]
        for interval_change in self._interval_changeRate:
            start = max(self._his_end_value[0], interval_change[0].start)  # cut off protruding years at start
            end = min(target_x, interval_change[0].end)  # cut off protruding years at end
            exp = max(0, end - start)  # clamp to 0, to ignore certain intervals
            result *= (1 + interval_change[1]) ** exp

        return result

    def get_historical_data_raw(self) -> (float, float):
        """ Getter for the last value of the historical data. """
        return self._his_end_value

    def get_interval_change_rate_raw(self) -> [(ctn.Interval, float)]:
        """ Getter for the list of interval-change-rate combinations used for the forecast. """
        return self._interval_changeRate
