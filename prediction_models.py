from collections import namedtuple
from enum import Enum

import numpy as np
import utility as uty
from statistics import mean

Exp = namedtuple("Exp", ["x0", "y0", "r"])  # y(x) = y0 * (1+r)^(x - x0)
Lin = namedtuple("Lin", ["k0", "k1"])
Quadr = namedtuple("Quadr", ["k0", "k1", "k2"])


class Coef:
    exp: Exp
    lin: Lin
    quadr: Quadr


Interval = namedtuple("Interval", ["start", "end"])


class StartPoint(Enum):
    LAST_AVAILABLE = 0
    AVERAGE_VALUE = 1
    MANUAL = 2

class CalculationType(Enum):
    EXPONENTIAL = 0
    LINEAR = 1
    QUADRATIC = 2


class Timeseries:
    _data: list[(float, float)]
    _coef = Coef()
    _calculation_type: CalculationType

    def __init__(self, data, calculation_type, rate_of_change=0):
        self._data = data

        if len(self._data) < 2:
            # with only one value available, no regression possible
            self._calculation_type = CalculationType.EXPONENTIAL
        elif len(self._data) < 3:
            # quadratic regression only possible with > 2 data points
            self._calculation_type = CalculationType.LINEAR
        else:
            self._calculation_type = calculation_type.QUADRATIC

        match self._calculation_type:
            case CalculationType.EXPONENTIAL:
                self._set_coef_exp(rate_of_change, StartPoint.LAST_AVAILABLE)
            case CalculationType.LINEAR:
                self._calc_coef_lin()
            case CalculationType.QUADRATIC:
                self._calc_coef_quadr()

    def get_prog(self, x):
        match self._calculation_type:
            case CalculationType.EXPONENTIAL:
                self.get_prog_exp(x)
            case CalculationType.LINEAR:
                self.get_prog_lin(x)
            case CalculationType.QUADRATIC:
                self.get_prog_quadr(x)

    def _set_coef_exp(self, rate_of_change, start_point: StartPoint, manual: (float, float) = (0, 0)):
        # TODO: implement manual startpoint in excel sheets
        (start_x, start_y) = (0, 0)
        match start_point:
            case StartPoint.LAST_AVAILABLE:
                (start_x, start_y) = self._data[-1]
            case StartPoint.AVERAGE_VALUE:
                (split_x, split_y) = zip(*self._data)
                start_x = mean(split_x)
                start_y = mean(split_y)
            case StartPoint.MANUAL:
                (start_x, start_y) = manual

        self._coef.exp = Exp(start_x, start_y, rate_of_change)

    def _calc_coef_lin(self):
        lin_coef = uty.linear_regression(self._data)
        self._coef.lin = Lin(lin_coef[0], lin_coef[1])

    def _calc_coef_quadr(self):
        quadr_coef = uty.quadratic_regression(self._data)
        self._coef.quadr = Quadr(quadr_coef[0], quadr_coef[1], quadr_coef[2])

    def get_data(self) -> list[(float, float)]:
        return self._data

    def get_prog_exp(self, x) -> float:
        return uty.exp_change(start_point=self._data[-1], change_rate=self._coef.exp.k0, target_x=x)

    def get_prog_lin(self, x) -> float:
        return uty.lin_prediction(self._coef.lin, x)

    def get_prog_quadr(self, x) -> float:
        return uty.quadr_prediction(self._coef.lin, x)


class PredictedTimeseries(Timeseries):
    _prediction: list[(float, float)]

    def __init__(self, historical_data, prediction_data, calculation_type: CalculationType = CalculationType.LINEAR,
                 rate_of_change=0):
        super().__init__(historical_data, calculation_type, rate_of_change)
        self._prediction = prediction_data

    def get_manual_prog(self, target_x: float):
        return [y for (x, y) in self._prediction if x == target_x][0]

    def get_prediction_raw(self):
        return self._prediction


class TimeStepSequence(Timeseries):
    _his_end_value: (float, float)
    _interval_changeRate: list[(Interval, float)]

    def __init__(self, historical_data, progression_data, calculation_type: CalculationType = CalculationType.LINEAR,
                 rate_of_change=0):
        super().__init__(historical_data, calculation_type, rate_of_change)

        # determine start value
        self._his_end_value = self._data[-1]

        # cut out unnecessary progression
        self._interval_changeRate = [progression_point for progression_point in progression_data
                                     if progression_point[0].end > self._his_end_value[0]]

        # map percentage to its hundredth
        self._interval_changeRate = [(prog[0], prog[1] / 100) for prog in self._interval_changeRate]

    def get_manual_prog(self, target_x: float):

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

    def get_historical_data_raw(self):
        return self._his_end_value
    def get_interval_change_rate_raw(self):
        return self._interval_changeRate
