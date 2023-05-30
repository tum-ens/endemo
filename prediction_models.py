from collections import namedtuple
from enum import Enum

import numpy as np
import utility as uty
from statistics import mean

Exp = namedtuple("Exp", ["x0", "y0", "r"]) # y(x) = y0 * (1+r)^(x - x0)
Lin = namedtuple("Lin", ["k0", "k1"])
Quadr = namedtuple("Quadr", ["k0", "k1", "k2"])
Coef = namedtuple("Coef", ["exp", "lin", "quadr"])

Interval = namedtuple("Interval", ["start", "end"])


class StartPoint(Enum):
    LAST_AVAILABLE = 0
    AVERAGE_VALUE = 1
    MANUAL = 2


class Timeseries:

    _data: list[(float, float)]
    _coef: Coef[Exp, Lin, Quadr]

    def __init__(self, data, setup_exp=False, setup_lin=False, setup_quadr=False, rate_of_change=np.NaN):
        self._data = data

        if setup_exp:
            assert(rate_of_change is not np.NaN)
            self._set_coef_exp(rate_of_change, StartPoint.LAST_AVAILABLE)
        if setup_lin:
            self._calc_coef_lin()
        if setup_quadr:
            self._calc_coef_quadr()

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

        self._coef.exp.x0 = start_x
        self._coef.exp.y0 = start_y
        self._coef.exp.r = rate_of_change

    def _calc_coef_lin(self):
        self._coef.lin = uty.linear_regression(self._data)

    def _calc_coef_quadr(self):
        self._coef.quadr = uty.quadratic_regression(self._data)

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

    def get_manual_prog(self, target_x: float):
        return [y for (x, y) in self._prediction if x == target_x][0]


class TimeStepSequence(Timeseries):

    _start_value: (float, float)
    _progression: list[(Interval, float)]

    def get_manual_prog(self, target_x: float):
        pass

