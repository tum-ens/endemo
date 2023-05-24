from collections import namedtuple
import numpy as np
import utility as uty
from statistics import mean

Const = namedtuple("Const", ["k0"])
Lin = namedtuple("Lin", ["k0", "k1"])
Quadr = namedtuple("Quadr", ["k0", "k1", "k2"])
Coef = namedtuple("Coef", ["const", "lin", "quadr"])

Interval = namedtuple("Interval", ["start", "end"])


class Timeseries:

    _data: list[(float, float)]
    _coef: Coef[Const, Lin, Quadr]

    def __init__(self, data, setup_const=False, setup_lin=False, setup_quadr=False, rate_of_change=np.NaN):
        self._data = data

        if setup_const:
            assert(rate_of_change is not np.NaN)
            self._set_coef_const(rate_of_change)
        if setup_lin:
            self._calc_coef_lin()
        if setup_quadr:
            self._calc_coef_quadr()

    def _set_coef_const(self, rate_of_change: float):
        self._coef.const.k0 = rate_of_change

    def _calc_coef_lin(self):
        self._coef.lin = uty.linear_regression(self._data)

    def _calc_coef_quadr(self):
        self._coef.quadr = uty.quadratic_regression(self._data)

    def get_data(self) -> list[(float, float)]:
        return self._data

    def get_prog_const(self, x) -> float:
        return uty.const_change(start_point=self._data[-1], change_rate=self._coef.const.k0, target_x=x)

    def get_prog_lin(self, x) -> float:
        return uty.lin_prediction(self._coef.lin, x)

    def get_prog_quadr(self, x) -> float:
        return uty.quadr_prediction(self._coef.lin, x)

    def get_prog_const_mean(self, x) -> float:
        avg = mean([y for (_, y) in self._data])
        last_x = self._data[-1][0]
        return uty.const_change((last_x, avg), self._coef.const.k0, x)


class PredictedTimeseries(Timeseries):

    _prediction: list[(float, float)]

    def get_manual_prog(self, target_x: float):
        return [y for (x, y) in self._prediction if x == target_x][0]


class TimeStepSequence(Timeseries):

    _start_value: (float, float)
    _progression: list[(Interval, float)]

    def get_manual_prog(self, target_x: float):
        pass

