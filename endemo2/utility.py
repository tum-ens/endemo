from __future__ import annotations

from typing import Any

import numpy as np
import matplotlib.pyplot as plt
import math
import pandas as pd

from endemo2.data_structures import prediction_models as pm


def str_dict(dictionary: dict):
    """
    Used to convert a dictionary to a string in a more readable form than if we would use the regular python
    implementation.

    Dictionary: {
    key : value,
    key : value,
    ...
    }

    :param dictionary: The dictionary to convert to string.
    :return: The string representation of the dictionary.
    """
    res = "\n"
    res += "Dictionary: {"
    for (a, b) in dictionary.items():
        if type(b) is dictionary:
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


def plot_timeseries_regression(dr: pm.TwoDseries, title: str = "", x_label: str = "", y_label: str = "") -> None:
    """
    Show a TwoDseries plotted with different optional labels.

    :param dr: The TwoDseries to be plotted.
    :param title: The title of the plot.
    :param x_label: The label for the x-axis of the plot.
    :param y_label: The label for the y-axis of the plot.
    """
    x, y = zip(*dr.get_data())

    coef = dr.get_coef()

    # Plot points
    plt.plot(x, y, 'o', color="grey", label="data points")

    # Plot exp regression
    plt.plot(x, [exp_change((coef._exp.x0, coef._exp.y0), coef._exp.r, e) for e in x], color="purple", label="exponential")

    # Plot linear regression
    plt.plot(x, [lin_prediction((coef._lin.k0, coef._lin.k1), e) for e in x], color="orange", label="linear")

    # Plot quadratic regression
    plt.plot(x, [quadr_prediction((coef._quadr.k0, coef._quadr.k1, coef._quadr.k2), e) for e in x], color="blue",
             label="quadratic")

    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)

    plt.legend(loc='best')
    plt.show()


def apply_all_regressions(data: list[(float, float)]) -> pm.Coef:
    """
    Applies all available regression algorithms to given data and returns coefficient object.

    :param data: Data that regression is applied on.
    :return: A coefficient object summarizing the results from all regressions.
    """
    result = pm.Coef()

    if len(data) == 0:
        return result

    if len(data) >= 2:
        lin_res = linear_regression(data)
        result.set_lin(lin_res[0], lin_res[1])

    if len(data) >= 3:
        quadr_res = quadratic_regression(data)
        result.set_quadr(quadr_res[0], quadr_res[1], quadr_res[2])

    return result


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


def quadratic_regression_delta(data: dict[str, pm.TwoDseries]) \
        -> ((float, float, float), dict[str, float]):
    """
    :todo: implement later

    :param dict data: The data on which linear regression is applied. It should be structured like {tag -> data list}
    :return: The calculated coefficients (k0, k1, k2) and the offset for each tag {tag -> offset}
    """
    N = len(data)

    e_1 = a_1 = b_1 = c_1 = 0
    e_2 = c_2 = 0
    e_3 = c_3 = 0

    # ??? what is to come ???

    dict_result_offsets = dict()
    for name, value in data.items():
        dict_result_offsets[name] = 0

    return (0, 0, 0), dict_result_offsets


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


def filter_out_nan_and_inf(data: [(float, float)]) -> [(float, float)]:
    """
    Filters out all entries in the list of tuples, where one of the values is either Inf or NaN.

    :param data: The list of tuples to filter
    :return: The filtered list of tuples
    """
    filter_lambda = \
        lambda xys: [(float(x), float(y)) for (x, y) in xys if is_permissible_float(x) and is_permissible_float(y)]
    return filter_lambda(data)


# zip 2 lists, where they have the same x value. Works only on ascending x values!!
def _zip_on_x_generator(a: [(float, float)], b: [(float, float)]) -> ((float, float), (float, float)):
    """
    A helper function for combine_data_on_x. This is a generator, that returns one value after another.
    Can be cast to list to apply on whole preprocessing at once and create a list as output of form [(a, b), (a, d)]

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


def zip_data_on_x(xys1: [(float, float)], xys2: [(float, float)], ascending_x=True) \
        -> [(float, float)]:
    """
    Zip the two lists of tuples on the condition that the first tuple entry matches.

    :param xys1: List to zip nr1 [(a,b)]
    :param xys2: List to zip nr2 [(c, d)]
    :param ascending_x: Indicates that the first tuple entry is ascending in the lists.
                        If true, a more efficient algorithm can be used.
    :return: The zipped list in format [(b, d)] for where a == c
    """
    res = []

    if ascending_x:
        # runtime in O(n)
        zipped = list(_zip_on_x_generator(xys1, xys2))
        res = list(map(lambda arg: (arg[0][1], arg[1][1]), zipped))
    else:
        # runtime in O(n^2)
        for i in range(0, len(xys1)):
            for j in range(0, len(xys2)):
                if xys1[i][0] == xys2[j][0]:
                    res.append((xys1[i][1], xys2[j][1]))
    return res


def zip_data_on_x_and_map(xys1: [(float, float)], xys2: [(float, float)], function) -> Any:
    """
    Combines two data lists and applies the given function to them.
    x-axis has to be ascending.

    :param [(float, float)] xys1: Data list one.
    :param [(float, float)] xys2: Data list two.
    :param function: The function that is applied. Should be of form lambda x y1 y2 -> ...
    :return: The result of the applied function.
    """
    zipped = list(_zip_on_x_generator(xys1, xys2))
    return [function(x1, y1, y2) for ((x1, y1), (x2, y2)) in zipped]


def map_data_y(xys: [(float, float)], function) -> [(float, float)]:
    """
    Applies the given function component-wise on the y-axis of the given data.

    :param xys: The given data.
    :param function: Function to apply to y-axis. Should be of form lambda x -> ...
    :return: The mapped data.
    """
    return [(x, function(y)) for (x, y) in xys]


def cut_after_x(data: [(float, float)], last_x: float) -> [(float, float)]:
    """
    Cuts the tail of a list, according to first entry of tuple being larger than last_x.

    :param data: The data list, whose tail will be cut off.
    :param last_x: The x-axis value indicating where to cut the list. (last_x is kept)
    :return: The cut data list.
    """
    if last_x is np.NaN:
        return data

    counter = 0
    for x, y in reversed(data):
        if x <= last_x:
            return data[:len(data)-counter]
        counter += 1
    return []


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

