import itertools
import os
import sys
from pathlib import Path

import seaborn as sns
from matplotlib import pyplot as plt

from endemo2.data_structures.enumerations import ForecastMethod
from endemo2.data_structures.prediction_models import TwoDseries, Coef
from endemo2.input_and_settings.input_manager import InputManager
from endemo2.output.output_utility import FileGenerator
from endemo2.utility import get_series_range


def save_plot(image_label, x_label, y_label, directory, file_name):
    """
    Sets the image and axis labels and saves the current plot to the given directory as filename.

    :param image_label: The label of the image.
    :param x_label: The label of the x-axis.
    :param y_label: The label of the y-axis.
    :param directory: The directory to save the plot into.
    :param file_name: The filename to save the plot as.
    """
    plt.title(image_label)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.legend(loc='upper right')

    if not os.path.exists(Path(directory)):
        os.makedirs(Path(directory))
    plt.savefig(directory / str(file_name + '.png'))
    plt.clf()


def plot_coef_in_range(label: str, start_end: (int, int), coef: Coef, color_lin, color_log, color_quadr, color_exp):
    """
    Adds all possible functions of a coefficient object to a plot.

    :param label: What the coefficients represent.
    :param start_end: The range, that the function should be plotted within.
    :param coef: The coef object that should be plotted.
    :param color_lin: The line color of the linear function.
    :param color_quadr: The line color of the quadratic function.
    :param color_exp: The line color of the exponential function.
    """
    (start, end) = start_end
    lin = coef.get_lin()
    log = coef.get_log()
    quadr = coef.get_quadr()
    exp = coef.get_exp()
    offset = coef.get_offset()

    x_axis = list(range(start, end + 1))
    if lin is not None:
        coef_func = [coef.get_lin_y(x) for x in x_axis]
        plt.plot(x_axis, coef_func, color=color_lin, label=label + " lin coef", linestyle="dashed")
    if log is not None:
        coef_func = [coef.get_log_y(x) for x in x_axis]
        plt.plot(x_axis, coef_func, color=color_log, label=label + " log coef", linestyle="dashed")
    if quadr is not None:
        if offset is not None:
            coef_func = [coef.get_quadr_offset_y(x) for x in x_axis]
            plt.plot(x_axis, coef_func, color=color_quadr,
                     label=label + " quadr coef delta", linestyle="dashed")
        else:
            coef_func = [coef.get_quadr_y(x) for x in x_axis]
            plt.plot(x_axis, coef_func, color=color_quadr, label=label + " quadr coef", linestyle="dashed")
    if exp is not None and exp[0] is not None:
        start = exp[0]
        x_exp = [start.x, start.x + 1, start.x + 2, start.x + 3, start.x + 4]
        coef_func = [coef.get_exp_y(x) for x in x_exp]
        plt.plot(x_exp, coef_func, color=color_exp, label=label + " exp coef", linestyle="dashed")


def plot_coef_with_method_in_range(label: str, start_end: (int, int), coef: Coef, color):
    """
    Adds the function of a coefficient object with chosen method to the current plot.

    :param label: What the coefficients represent.
    :param start_end: The range, that the function should be plotted within.
    :param coef: The coef object, whose chosen method function should be plotted.
    :param color: The color of the line of the function.
    """
    (start, end) = start_end
    x_axis = range(start, end + 1)
    if coef.get_method() == ForecastMethod.EXPONENTIAL:
        (start, end) = coef.get_exp()[0]
        x_axis = range(int(start), int(end) + 5)
    coef_func = [coef.get_function_y(x) for x in x_axis]
    plt.plot(x_axis, coef_func, color=color, label=label + " regression", linestyle="dashed")


def plot_historical_data(tds: TwoDseries, color, label):
    """
    Add the data of a TwoDseries to a plot. If there is only one data point, a dot is plotted, else a line over the
    whole data.

    :param tds: The series whose historical data should be plotted.
    :param color: The color of the plotted historical data.
    :param label: The label for the historical data line.
    """
    if len(tds.get_data()) == 0:
        # empty
        plt.plot([], [], 'o', color=color, label=label)
        return

    x, y = zip(*tds.get_data())
    # Plot points
    if len(x) < 2:
        plt.plot(x, y, 'o', color=color, label=label)
    else:
        plt.plot(x, y, color=color, label=label)


def plot_series_detailed(series: TwoDseries, colors, country_name):
    """
    Add a series to a plot. Plot historical data and all coefficients.

    :param series: The series that should be plotted.
    :param colors: A color palette to use.
    :param country_name: The name of the country the TwoDseries belongs to.
    """
    plot_historical_data(series, next(colors), country_name + " historical")
    interval = get_series_range([series])
    plot_coef_in_range(country_name, interval, series.get_coef(), next(colors), next(colors), next(colors), next(colors))


def save_series_plot(input_manager: InputManager, folder, series: TwoDseries, x_label, y_label, back_label, front_label):
    """
    Saves a series plot of a product in a country to a file.

    :param input_manager: The input_manager to get the output path from.
    :param folder: The path, relative to the output folder, the result should be saved to.
    :param series: The TwoDseries that should be plotted.
    :param x_label: The label for the x-axis.
    :param y_label: The label for the y-axis.
    :param front_label: Label used at the front of the image name and file name.
    :param back_label: Label used at the back of the image name and file name.
    """
    colors = itertools.cycle(sns.color_palette())

    plot_series_detailed(series, colors, back_label)

    image_label = front_label + " - " + back_label
    directory = input_manager.output_path / FileGenerator.get_day_directory() / folder
    file_name = front_label + "_" + y_label + "-vs-" + x_label + "_" + back_label

    save_plot(image_label, x_label, y_label, directory, file_name)


def plot_series_simple(series: TwoDseries, colors, label):
    """
    Plot a series historical data and coefficients of the chosen method.

    :param series: The series to plot.
    :param colors: The color palette to use.
    :param label: The label of the series.
    """
    plot_historical_data(series, next(colors), label)
    interval = get_series_range([series])
    plot_coef_with_method_in_range(label, interval, series.get_coef(), next(colors))


def save_multiple_series_plot(input_manager: InputManager, folder, tdss: [TwoDseries], labels: [str],
                              x_label: str, y_label: str, back_label: str, front_label: str):
    """
    Plots multiple TwoDseries into the same image and saves the plot.

    :param input_manager: The input_manager to get the output path from.
    :param folder: The path, relative to the output folder, the result should be saved to.
    :param tdss: The TwoDseries that should be plotted.
    :param labels: The labels for all TwoDseries in order.
    :param x_label: The label for the x-axis.
    :param y_label: The label for the y-axis.
    :param front_label: Label used at the front of the image name and file name.
    :param back_label: Label used at the back of the image name and file name.
    """
    colors = itertools.cycle(sns.color_palette())

    for series, label in list(zip(tdss, labels)):
        plot_series_simple(series, colors, label)

    image_label = front_label + " - " + back_label
    directory = input_manager.output_path / FileGenerator.get_day_directory() / folder
    file_name = front_label + "_" + y_label + "-vs-" + x_label + "_" + back_label

    save_plot(image_label, x_label, y_label, directory, file_name)
