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

def const_change(start_point: (float, float), change_rate: float, target_x: float) -> float:
    (start_x, start_y) = start_point
    result = start_point + (target_x-start_x) * change_rate
    return result

def quadratic_regression_delta(data: list[(float, float)], visualize: bool = False) \
        -> ((float, float, float), dict[str, float]):

    N = len(data)

    e_1 = a_1 = b_1 = c_1 = 0
    e_2 = c_2 = 0
    e_3 = c_3 = 0

    # ??? what is to come ???

    pass

def filter_out_NaN_and_Inf(data: list[(float, float)]):
    filter_out_NaN = lambda data: [(x, y) for (x, y) in data if not math.isnan(x) and not math.isnan(y)]
    filter_out_Inf = lambda data: [(x, y) for (x, y) in data if not math.isinf(x) and not math.isinf(y)]

    return filter_out_Inf(filter_out_NaN(data))

def combine_data_on_x(new_x: list[(float, float)], new_y: list[(float, float)]):
    pass


