import collections as coll
import enum
import numpy as np
import statistics as st

from endemo2 import utility as uty
from endemo2 import control_parameters as cp
from endemo2 import containers as ctn

Exp = coll.namedtuple("Exp", ["x0", "y0", "r"])  # y(x) = y0 * (1+r)^(x - x0)
Lin = coll.namedtuple("Lin", ["k0", "k1"])
Quadr = coll.namedtuple("Quadr", ["k0", "k1", "k2"])


class Coef:
    """
    The container for the coefficients of different forecast methods.

    :ivar (x0, y0, r) exp:
        (x0, y0) is the start point for the exponential calculation and r is the growth rate.
    :ivar (k0, k1) lin: Used for the calculation f(x) = k0 + k1 * x
    :ivar (k0, k1, k2) quadr: Used for the calculation f(x) = k0 + k1 * x + k2 * x^2
    """
    exp: Exp
    lin: Lin
    quadr: Quadr

    def __init__(self):
        self.exp = Exp(0, 0, 0)
        self.lin = Lin(0, 0)
        self.quadr = Quadr(0, 0, 0)


class StartPoint(enum.Enum):
    """ Denotes the type of start points used for the exponential forecast method. """
    LAST_AVAILABLE = 0
    AVERAGE_VALUE = 1
    MANUAL = 2


class Timeseries:
    """
    A Timeseries holds information about a process' values from the past and provides projections into the future.

    :param data: The historical data given for this timeseries.
    :param calculation_type: The forecast method, that should be used.
    :param rate_of_change: The manually given rate of change for the exponential forecast method.

    :ivar [(float, float)] _data: The historical data for this timeseries.
    :ivar Coef _coef: All the coefficients for different forecast methods.
    :ivar ForecastMethod _calculation_type: The currently selected forecast method that should be used for projections.
    """

    def __init__(self, data: [(float, float)], calculation_type: cp.ForecastMethod, rate_of_change=0.0):
        self._coef = Coef()
        self._data = data

        if len(self._data) < 2:
            # with only one value available, no regression possible
            self._calculation_type = cp.ForecastMethod.EXPONENTIAL
        elif len(self._data) < 3 and calculation_type is not cp.ForecastMethod.EXPONENTIAL:
            # quadratic regression only possible with > 2 data points
            self._calculation_type = cp.ForecastMethod.LINEAR
        else:
            self._calculation_type = calculation_type

        # calculate all coefficients
        self._set_coef_exp(rate_of_change, StartPoint.LAST_AVAILABLE)
        self._calc_coef_lin()
        self._calc_coef_quadr()

    def get_prog(self, x) -> float:
        """
        Getter for the prognosis of this timeseries.

        :param x: The x-axis value. Example: target year for projection into the future.
        :return: The estimated y-axis value for the target x.
        """
        match self._calculation_type:
            case cp.ForecastMethod.EXPONENTIAL:
                return self.get_prog_exp(x)
            case cp.ForecastMethod.LINEAR:
                return self.get_prog_lin(x)
            case cp.ForecastMethod.QUADRATIC:
                return self.get_prog_quadr(x)

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

        self._coef.exp = Exp(start_x, start_y, rate_of_change)

    def _calc_coef_lin(self):
        """ Calculates and sets the coefficient for the linear forecast method. """
        if len(self._data) < 2:
            if len(self._data) == 0:
                self._coef.lin = Lin(0, 0)
            else:
                self._coef.lin = Lin(self._data[0][1], 0)
            return
        lin_coef = uty.linear_regression(self._data)
        self._coef.lin = Lin(lin_coef[0], lin_coef[1])

    def _calc_coef_quadr(self):
        """ Calculates and sets the coefficient for the quadratic forecast method. """
        if len(self._data) < 3:
            if len(self._data) == 0:
                self._coef.lin = Quadr(0, 0, 0)
            else:
                self._coef.lin = Quadr(self._data[0][1], 0, 0)
            return
        quadr_coef = uty.quadratic_regression(self._data)
        self._coef.quadr = Quadr(quadr_coef[0], quadr_coef[1], quadr_coef[2])

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
        return uty.exp_change((self._coef.exp.x0, self._coef.exp.y0), self._coef.exp.r, x)

    def get_prog_lin(self, x) -> float:
        """
        Get the prognosis of the y-axis value for a target x-axis value with the linear forecast method.

        :param x: The target x-axis value.
        :return: The predicted y value at x-axis value x.
        """
        return uty.lin_prediction(self._coef.lin, x)

    def get_prog_quadr(self, x) -> float:
        """
        Get the prognosis of the y-axis value for a target x-axis value with the quadratic forecast method.

        :param x: The target x-axis value.
        :return: The predicted y value at x-axis value x.
        """
        return uty.quadr_prediction(self._coef.lin, x)


class PredictedTimeseries(Timeseries):
    """
    A variant of the timeseries class, where there is a manual forecast available that is read from the input and used
    for the forecast.

    :param [(float, float)] historical_data: The historical data. Passed onto parent class.
    :param [(float, float)] prediction_data: The manual prediction data. This is saved and used for the forecast.
    :param ForecastMethod calculation_type: The forecast type, should the parent class be used instead. Is passed on to
        the parent class.
    :param float rate_of_change: The rate of change for the exponential forecast method, should this one be selected
        for use in the parent class.

    :ivar [(float, float)] _prediction: The manual prediction, which is used for the forecast.
    """
    def __init__(self, historical_data: [(float, float)], prediction_data: [(float, float)],
                 calculation_type: cp.ForecastMethod = cp.ForecastMethod.LINEAR, rate_of_change=0.0):
        super().__init__(historical_data, calculation_type, rate_of_change)
        self._prediction = prediction_data

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


class TimeStepSequence(Timeseries):
    """
    A variant of the timeseries class, where there is a forecast given in the shape of intervals with an exponential
    growth rate.

    :param [(float, float)] historical_data: The historical data. Passed onto parent class.
    :param [(Interval, float)] progression_data: The manual progression data in form of an interval in combination with
        the exponential growth rate.
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
                 calculation_type: cp.ForecastMethod = cp.ForecastMethod.LINEAR,
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

        # calculate resulting gdp in future
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
