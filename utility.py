from __future__ import annotations

import warnings
from collections import namedtuple
from typing import Tuple, List
import numpy as np
import matplotlib.pyplot as plt
import math

import pandas as pd

from prediction_models import Timeseries


def str_dict(dict):
    res = "\n"
    res += "Dictionary: {"
    for (a, b) in dict.items():
        if type(b) is dict:
            res += str(a) + ": " + str_dict(b) + ", "
        else:
            res += str(a) + ": " + str(b) + ", "
    res += "}"
    return res


def is_zero(xs: [float]):
    for x in xs:
        if float(x) != 0 and float(x) != np.nan:
            return False
    return True


def is_tuple_list_zero(xys: [(float, float)]):
    if not xys or len(xys) == 0:
        return True
    else:
        return is_zero(list(zip(*xys))[1])


def plot_timeseries(ts: Timeseries):
    x, y = zip(*ts.get_data())

    coef = ts.get_coef()

    # Plot points
    plt.plot(x, y, 'o', color="grey")

    # Plot exp regression
    plt.plot(x, [exp_change((coef.exp.x0, coef.exp.y0), coef.exp.r, e) for e in x], color="purple")

    # Plot linear regression
    plt.plot(x, [lin_prediction((coef.lin.k0, coef.lin.k1), e) for e in x], color="orange")

    # Plot quadratic regression
    plt.plot(x, [quadr_prediction((coef.quadr.k0, coef.quadr.k1, coef.quadr.k2), e) for e in x], color="blue")

    plt.show()

def linear_regression(data: list[(float, float)], visualize: bool = False) -> (float, float):
    # Unzip data List
    x, y = zip(*data)

    # Use numpy linear regression
    ks = np.polyfit(x, y, 1)
    (k0, k1) = (float(ks[1]), float(ks[0]))

    if visualize:
        # Plot points
        plt.plot(x, y, 'o', color="green")

        # Plot regression line
        plt.plot(x, [k1 * e + k0 for e in x], color="green")

        plt.show()

    return k0, k1


def quadratic_regression(data: list[(float, float)], visualize: bool = False) -> (float, float, float):
    # Unzip data List
    x, y = zip(*data)

    # Use numpy linear regression
    ks = np.polyfit(x, y, 2)
    (k0, k1, k2) = (float(ks[2]), float(ks[1]), float(ks[0]))

    if visualize:
        # Plot points
        plt.plot(x, y, 'o', color="blue")

        # Plot regression line
        plt.plot(x, [k2 * e ** 2 + k1 * e + k0 for e in x], color="blue")

        plt.show()

    return k0, k1, k2


def quadratic_regression_delta(data: list[(float, float)], visualize: bool = False) \
        -> ((float, float, float), dict[str, float]):
    N = len(data)

    e_1 = a_1 = b_1 = c_1 = 0
    e_2 = c_2 = 0
    e_3 = c_3 = 0

    # ??? what is to come ???

    pass


def exp_change(start_point: (float, float), change_rate: float, target_x: float) -> float:
    (start_x, start_y) = start_point
    result = start_y * (1 + change_rate) ** (target_x - start_x)
    return result


def lin_prediction(coef: (float, float), target_x: float):
    k0 = coef[0]
    k1 = coef[1]
    return k0 + k1 * target_x


def quadr_prediction(coef: (float, float, float), target_x: float):
    k0 = coef[0]
    k1 = coef[1]
    k2 = coef[2]
    return k0 + k1 * target_x + k2 * target_x ** 2


def is_permissible_float(x: str):
    try:
        return not math.isnan(float(x)) and not math.isinf(float(x))
    except ValueError:
        return False


def filter_out_nan_and_inf(data: list[(float, float)]):
    filter_lambda = \
        lambda xys: [(float(x), float(y)) for (x, y) in xys if is_permissible_float(x) and is_permissible_float(y)]
    return filter_lambda(data)


# zip 2 lists, where they have the same x value. Works only on ascending x values!!
def zip_on_x(a: list[(float, float)], b: list[(float, float)]) -> ((float, float), (float, float)):
    j = i = 0
    while True:
        if i >= len(a) or j >= len(b):
            break
        elif float(a[i][0]) < float(b[j][0]):
            i += 1
            continue
        elif float(a[i][0]) == float(b[j][0]):
            yield a[i], b[j]
            i += 1
            continue
        elif float(a[i][0]) > float(b[j][0]):
            j += 1
            continue


def combine_data_on_x(new_x: list[(float, float)], new_y: list[(float, float)], ascending_x=False):
    res = []

    if ascending_x:
        # runtime in O(n)
        zipped = list(zip_on_x(new_x, new_y))
        res = list(map(lambda arg: (arg[0][1], arg[1][1]), zipped))
    else:
        warnings.warn("Are you sure, that your data on x axis is not ascending?")
        # runtime in O(n^2)
        for i in range(0, len(new_x)):
            for j in range(0, len(new_y)):
                if new_x[i][0] == new_y[j][0]:
                    res.append((new_x[i][1], new_y[j][1]))
    return res


def cut_after_x(data: [(float, float)], last_x: float):
    if last_x is np.NaN:
        return data

    counter = 0
    for x, y in reversed(data):
        if x < last_x:
            return data[:-counter]
        counter += 1


def convert_table_to_filtered_data_series_per_country(df: pd.DataFrame) -> dict:
    dict_out = dict()
    it = pd.DataFrame(df).itertuples()
    for row in it:
        country_name = row[1]
        zipped = list(zip(list(df)[1:], row[2:]))
        his_data = filter_out_nan_and_inf(zipped)
        dict_out[country_name] = his_data
    return dict_out

