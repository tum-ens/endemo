import warnings
from collections import namedtuple
from typing import Tuple, List
import numpy as np
import matplotlib.pyplot as plt
import math

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
        plt.plot(x, [k2 * e**2 + k1 * e + k0 for e in x], color="blue")

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
    result = start_y * (1 + change_rate)**(target_x - start_x)
    return result


def lin_prediction(coef: (float, float), target_x: float):
    k0 = coef[0]
    k1 = coef[1]
    return k0 + k1 * target_x


def quadr_prediction(coef: (float, float, float), target_x: float):
    k0 = coef[0]
    k1 = coef[1]
    k2 = coef[2]
    return k0 + k1 * target_x + k2 * target_x**2

def filter_out_NaN_and_Inf(data: list[(float, float)]):
    filter_out_NaN = lambda data: [(x, y) for (x, y) in data if not math.isnan(x) and not math.isnan(y)]
    filter_out_Inf = lambda data: [(x, y) for (x, y) in data if not math.isinf(x) and not math.isinf(y)]

    return filter_out_Inf(filter_out_NaN(data))


# zip 2 lists, where they have the same x value. Works only on ascending x values!!
def zip_on_x(a: list[(float, float)], b: list[(float, float)]) -> ((float, float), (float, float)):
    j = i = 0
    while True:
        if i >= len(a) or j >= len(b):
            break
        elif a[i][0] < b[j][0]:
            i += 1
            continue
        elif a[i][0] == b[j][0]:
            yield a[i], b[j]
            i += 1
            continue
        elif a[i][0] > b[j][0]:
            j += 1
            continue


def combine_data_on_x(new_x: list[(float, float)], new_y: list[(float, float)], ascending_x = False):
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

