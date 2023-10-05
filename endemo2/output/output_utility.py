"""
This module contains utility functions and classes to more easily generate output files.
"""
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from endemo2.data_structures.prediction_models import Timeseries, Coef
from endemo2.data_structures.containers import Demand
from endemo2.input_and_settings.input_manager import InputManager


def get_day_folder_path(input_manager: InputManager):
    """ Get the path to the day folder. """
    # generate directory based on date
    day_directory_name = FileGenerator.get_day_directory()

    # create directory when not present
    day_folder_path = ensure_directory_exists(input_manager.output_path / day_directory_name)
    return day_folder_path


def ensure_directory_exists(path: Path) -> Path:
    """ Utility function to wrap a path to a directory that creates the directory if needed. """
    if not os.path.exists(path):
        os.makedirs(path)
    return path


class FileGenerator(object):
    """
    A tool to more easily generate output files.

    :ivar Input input_manager: A reference to the input_manager that holds all preprocessing.
    :ivar pd.ExcelWriter excel_writer: The excel writer used for writing the file.
    :ivar str current_sheet_name: Keeps track of the current sheet name that new entries (add_entry) will be written to.
    :ivar dict current_out_dict: Keeps the entries that are added.
        When writing the file, these are converted to a table.
    :ivar str out_file_path: The output file path. Mainly used as attribute for debugging.
    """

    # Example usage:
    #    fg = FileGenerator(input_manager, out.xlsx)
    #    with fg
    #        fg.start_sheet("Data")
    #        fg.add_entry("Country", "Belgium")
    #        fg.add_entry("Value", 0.5)
    #        fg.start_sheet("Info")
    #        fg.add_entry("Sources", "[1] ...")
    #        ...

    def __init__(self, input_manager, directory, filename, output_path=None):

        if output_path is None:
            output_path = input_manager.output_path

        # generate directory based on date
        day_directory_name = FileGenerator.get_day_directory()

        # create directory when not present
        if directory == "":
            if not os.path.exists(output_path):
                os.makedirs(output_path)
            self.out_file_path = output_path / day_directory_name / filename
        else:
            if not os.path.exists(output_path / day_directory_name / directory):
                os.makedirs(output_path / day_directory_name / directory)
            self.out_file_path = output_path / day_directory_name / directory / filename

        self.input_manager = input_manager
        self.excel_writer = pd.ExcelWriter(self.out_file_path)
        self.current_sheet_name = ""
        self.current_out_dict = dict()

    def __enter__(self):
        self.current_sheet_name = ""
        self.current_out_dict = dict()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save_file()

    @classmethod
    def get_day_directory(cls):
        return "results_" + datetime.today().strftime('%Y-%m-%d')

    def add_complete_column(self, column_name: str, column_content: []):
        """
        Add a complete column to sheet.
        But pay attention! In the end of the sheet, all columns have to have the same length.
        """
        self.current_out_dict[column_name] = column_content

    def start_sheet(self, name):
        """ Start editing a new sheet with name "name". """
        if self.current_sheet_name != "":
            self.end_sheet()
        self.current_sheet_name = name
        self.current_out_dict = dict()

    def print_length_of_all_entries(self):
        """ Used for debugging purposes. """
        print("---")
        for key, value in self.current_out_dict.items():
            print(str(key) + ": " + str(len(value)))
        print("---")

    def print_all_entries(self):
        """ Used for debugging purposes. """
        print("---")
        for key, value in self.current_out_dict.items():
            print(str(key) + ": " + str(value))
        print("---")

    def end_sheet(self):
        """ Stop editing current sheet. """
        df_out = pd.DataFrame(self.current_out_dict)
        df_out.to_excel(self.excel_writer, index=False, sheet_name=self.current_sheet_name, float_format="%.12f")
        self.current_sheet_name = ""
        self.current_out_dict = dict()

    def add_entry(self, column_name, value):
        """
        Add an entry to a column. But pay attention! In the end of the sheet, all columns have to have the same length.
        """
        if column_name not in self.current_out_dict.keys():
            self.current_out_dict[column_name] = []
        self.current_out_dict[column_name].append(value)

    def save_file(self):
        """ Save the dictionary that was filled by this object to a file. """
        if self.current_sheet_name != "":
            self.end_sheet()
        self.excel_writer.close()


def shortcut_save_timeseries_print(fg, interval: (float, float), data: [(float, float)]):
    """ Shortcut to correctly output a timeseries, when data does potentially not cover every year."""

    (from_year, to_year) = interval

    i = from_year
    for (year, value) in data:
        while i < year:
            fg.add_entry(i, "")
            i += 1
        if i == year:
            fg.add_entry(year, value)
            i += 1

    while i <= to_year:
        fg.add_entry(i, "")
        i += 1


def shortcut_sc_output(fg, sc):
    """ A shortcut to output the contents of a specific consumption object. """
    fg.add_entry("Electricity [GJ/t]", sc.electricity)
    fg.add_entry("Heat [GJ/t]", sc.heat)
    fg.add_entry("Hydrogen [GJ/t]", sc.hydrogen)
    fg.add_entry("max. subst. of heat with H2 [%]", sc.max_subst_h2)


def shortcut_demand_table(fg: FileGenerator, demand: Demand):
    """ A shortcut to output the contents of a Demand object. """
    fg.add_entry("Electricity [TWh]", demand.electricity)
    fg.add_entry("Heat [TWh]", demand.heat.get_sum())
    fg.add_entry("Hydrogen [TWh]", demand.hydrogen)
    fg.add_entry("Heat Q1 [TWh]", demand.heat.q1)
    fg.add_entry("Heat Q2 [TWh]", demand.heat.q2)
    fg.add_entry("Heat Q3 [TWh]", demand.heat.q3)
    fg.add_entry("Heat Q4 [TWh]", demand.heat.q4)


def generate_timeseries_output(fg: FileGenerator, ts: Timeseries, year_range):
    """ Generate output for a Timeseries object. """
    # output coef
    coef = ts.get_coef()
    shortcut_coef_output(fg, coef)

    # output data
    shortcut_save_timeseries_print(fg, year_range, ts.get_data())


def shortcut_coef_output(fg: FileGenerator, coef: Coef):
    """ A shortcut to easily output the contents of a coefficient object. """

    forecast_method = coef._method
    exp_coef = coef._exp
    lin_coef = coef._lin
    quadr_coef = coef._quadr
    offset = coef._offset

    if forecast_method is not None:
        fg.add_entry("Selected Forecast Method", str(forecast_method))
    else:
        fg.add_entry("Selected Forecast Method", "")

    if exp_coef is not None:
        if exp_coef[0] is not None:
            fg.add_entry("Exponential Start Point", "(" + str(exp_coef[0][0]) + ", " + str(exp_coef[0][1]) + ")")
            if exp_coef[1] is not None:
                fg.add_entry("Exponential Change Rate", exp_coef[1])
            else:
                fg.add_entry("Exponential Change Rate", "")
        elif exp_coef[1] is not None:
            fg.add_entry("Exponential Start Point", "")
            fg.add_entry("Exponential Change Rate", exp_coef[1])
        else:
            fg.add_entry("Exponential Start Point", "")
            fg.add_entry("Exponential Change Rate", "")
    else:
        fg.add_entry("Exponential Start Point", "")
        fg.add_entry("Exponential Change Rate", "")
    if lin_coef is not None:
        fg.add_entry("Linear k0", lin_coef[0])
        fg.add_entry("Linear k1", lin_coef[1])
    else:
        fg.add_entry("Linear k0", "")
        fg.add_entry("Linear k1", "")
    if quadr_coef is not None:
        fg.add_entry("Quadratic k0", quadr_coef[0])
        fg.add_entry("Quadratic k1", quadr_coef[1])
        fg.add_entry("Quadratic k2", quadr_coef[2])
    else:
        fg.add_entry("Quadratic k0", "")
        fg.add_entry("Quadratic k1", "")
        fg.add_entry("Quadratic k2", "")
    if offset is not None:
        fg.add_entry("Offset", offset)
    else:
        fg.add_entry("Offset", "")
