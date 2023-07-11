from __future__ import annotations

import warnings
import numpy as np
import matplotlib.pyplot as plt
import math
import pandas as pd

from endemo2 import prediction_models as pm


def str_dict(dict):
    """
    Used to convert a dictionary to a string in a more readable form than if we would use the regular python
    implementation.

    Dictionary: {
    key : value,
    key : value,
    ...
    }

    :param dict: The dictionary to convert to string.
    :return: The string representation of the dictionary.
    """
    res = "\n"
    res += "Dictionary: {"
    for (a, b) in dict.items():
        if type(b) is dict:
            res += str(a) + ": " + str_dict(b) + ", "
        else:
            res += str(a) + ": " + str(b) + ", "
    res += "}"
    return res


def is_zero(xs: [float]) -> bool:
    """
    Checks for a list of floats if there are only zeroes present in it. Returns also true for empty list.

    :param xs: The list to check
    :return: True if contains only zeros, False otherwise.
    """
    for x in xs:
        if float(x) != 0 and float(x) != np.nan:
            return False
    return True


def is_tuple_list_zero(xys: [(float, float)]) -> bool:
    """
    A wrapper for the is_zero function that applies it on a list of tuples, where only the second entries in a tuple
    are checked for being zero.

    :param xys: The tuple list which should be checked for zeroes.
    :return: True if the left column/entries of the list of tuples only contains zeros.
    """
    if not xys or len(xys) == 0:
        return True
    else:
        return is_zero(list(zip(*xys))[1])


def plot_timeseries(ts: pm.Timeseries):
    """ Quickly plots all forecast methods of a timeseries, without using labels. """
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
    """
    Apply linear regression on data and return the coefficients.

    :param data: The data on which linear regression is applied.
    :param visualize: Indicate, whether the result should be immediately plotted.
    :return: The calculated coefficients (k0, k1)
    """
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
    """
    Apply quadratic regression on data and return the coefficients.

    :param data: The data on which linear regression is applied.
    :param visualize: Indicate, whether the result should be immediately plotted.
    :return: The calculated coefficients (k0, k1, k3)
    """
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
    """
    :todo: implement later

    :param data: The data on which linear regression is applied.
    :param visualize: Indicate, whether the result should be immediately plotted.
    :return: The calculated coefficients (k0, k1)
    """
    N = len(data)

    e_1 = a_1 = b_1 = c_1 = 0
    e_2 = c_2 = 0
    e_3 = c_3 = 0

    # ??? what is to come ???

    pass


def exp_change(start_point: (float, float), change_rate: float, target_x: float) -> float:
    """
    Calculates the result of exponential growth on a start point.

    .. math::
        y_{new} = y_{start} * (1+r)^{x_{new}-x_{start}}

    :param start_point: (x_start, y_start)
    :param change_rate: r
    :param target_x: x_new
    :return: y_new
    """
    (start_x, start_y) = start_point
    result = start_y * (1 + change_rate) ** (target_x - start_x)
    return result


def lin_prediction(coef: (float, float), target_x: float):
    """
    Calculates the result of a linear function according to given coefficients.

    .. math::
        f(x)=k_0+k_1*x

    :param coef: (k_0, k_1)
    :param target_x: x
    :return: f(x)
    """
    k0 = coef[0]
    k1 = coef[1]
    return k0 + k1 * target_x


def quadr_prediction(coef: (float, float, float), target_x: float):
    """
    Calculates the result of a quadratic function according to given coefficients.

    .. math::
        f(x)=k_0+k_1*x+k_2*x^2

    :param coef: (k_0, k_1, k_2)
    :param target_x: x
    :return: f(x)
    """
    k0 = coef[0]
    k1 = coef[1]
    k2 = coef[2]
    return k0 + k1 * target_x + k2 * target_x ** 2


def is_permissible_float(x: str):
    """
    Checks if a string could be converted to a float that is not NaN or Inf, without throwing an exception.

    :param x: The string to check for float conversion.
    :return: True if it can be converted to float, else False.
    """
    try:
        return not math.isnan(float(x)) and not math.isinf(float(x))
    except ValueError:
        return False


def filter_out_nan_and_inf(data: list[(float, float)]) -> [(float, float)]:
    """
    Filters out all entries in the list of tuples, where one of the values is either Inf or NaN.

    :param data: The list of tuples to filter
    :return: The filtered list of tuples
    """
    filter_lambda = \
        lambda xys: [(float(x), float(y)) for (x, y) in xys if is_permissible_float(x) and is_permissible_float(y)]
    return filter_lambda(data)


# zip 2 lists, where they have the same x value. Works only on ascending x values!!
def zip_on_x(a: list[(float, float)], b: list[(float, float)]) -> ((float, float), (float, float)):
    """
    A helper function for combine_data_on_x. This is a generator, that returns one value after another.
    Can be cast to list to apply on whole input at once and create a list as output of form [(a, b), (a, d)]

    :param a: List 1 [(a, b)]
    :param b: List 2 [(c, d)]
    :return: Next zipped entry in format ((a, b), (a, d)) for where a == c
    """
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


def combine_data_on_x(x: list[(float, float)], y: list[(float, float)], ascending_x=False) \
        -> [(float, float), (float, float)]:
    """
    Zip the two lists of tuples on the condition that the first tuple entry matches.

    :param x: List to zip nr1 [(a,b)]
    :param y: List to zip nr2 [(c, d)]
    :param ascending_x: Indicates that the first tuple entry is ascending in the lists.
                        If true, a more efficient algorithm can be used.
    :return: The zipped list in format [(b, d)] for where a == c
    """
    res = []

    if ascending_x:
        # runtime in O(n)
        zipped = list(zip_on_x(x, y))
        res = list(map(lambda arg: (arg[0][1], arg[1][1]), zipped))
    else:
        warnings.warn("Are you sure, that your data on x axis is not ascending?")
        # runtime in O(n^2)
        for i in range(0, len(x)):
            for j in range(0, len(y)):
                if x[i][0] == y[j][0]:
                    res.append((x[i][1], y[j][1]))
    return res


def cut_after_x(data: [(float, float)], last_x: float) -> [(float, float)]:
    """
    Cuts the tail of a list, according to first entry of tuple being larger than last_x.

    :param data: The data list, whose tail will be cut off.
    :param last_x: The x-axis value indicating where to cut the list. (inclusive)
    :return: The cut data list.
    """
    if last_x is np.NaN:
        return data

    counter = 0
    for x, y in reversed(data):
        if x <= last_x:
            return data[:-counter]
        counter += 1


def convert_table_to_filtered_data_series_per_country(df: pd.DataFrame) -> dict:
    """
    Create a dictionary from a table.
    A key is the first value in row. The corresponding value is a list [column_name, column_value] for the whole row.

    :param df: The dataframe to process
    :return: The row-oriented dictionary { first_row_entry -> [column_name, column_value]}
    """
    dict_out = dict()
    it = pd.DataFrame(df).itertuples()
    for row in it:
        country_name = row[1]
        zipped = list(zip(list(df)[1:], row[2:]))
        his_data = filter_out_nan_and_inf(zipped)
        dict_out[country_name] = his_data
    return dict_out

