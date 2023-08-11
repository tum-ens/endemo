"""
This module contains all functions that generate output files from the preprocessor.
"""
import itertools
import os
from pathlib import Path

from matplotlib import pyplot as plt
import seaborn as sns

from endemo2.data_structures.enumerations import DemandType, ForecastMethod
from endemo2.output.output_utility import FileGenerator, generate_timeseries_output, get_series_range, \
    shortcut_coef_output, get_day_folder_path, ensure_directory_exists
from endemo2.output.plot_utility import save_series_plot, save_multiple_series_plot
from endemo2.data_structures.prediction_models import Coef, Timeseries, TwoDseries
from endemo2.input_and_settings import input
from endemo2.preprocessing.preproccessing_step_two import GroupManager, CountryGroupJoinedDiversified, \
    CountryGroupJoined
from endemo2.preprocessing.preprocessing_step_one import CountryPreprocessed, ProductPreprocessed
from endemo2 import utility as uty
from endemo2.output.plot_utility import *


def generate_preprocessing_output(input_manager, preprocessor):
    """
    Calls all generate_x_output functions of this module that should be used to generate output of the preprocessor.
    """

    folder_name = "preprocessed"

    generate_amount_timeseries_output(folder_name, input_manager, preprocessor.countries_pp)
    generate_amount_per_gdp_coef_output(folder_name, input_manager, preprocessor.countries_pp)
    generate_specific_consumption_output(folder_name, input_manager, preprocessor.countries_pp)
    generate_country_group_output(folder_name, input_manager, preprocessor.group_manager)

    #if input_manager.ctrl.general_settings.toggle_graphical_output:
        #generate_visual_output(folder_name, input_manager, preprocessor.countries_pp)


def generate_country_group_output(folder, input_manager: input.Input, group_manager: GroupManager):

    filename = "ind_coef_country_group.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name in group_manager.separate_countries_group.keys():
            fg.start_sheet(product_name)

            # output joined groups
            for joined_group in group_manager.joined_groups[product_name]:
                str_countries_in_group = ""
                for country_name in joined_group.get_countries_in_group():
                    str_countries_in_group += country_name + ";"
                group_coef = joined_group.get_coef()
                for country_name in joined_group.get_countries_in_group():
                    fg.add_entry("Country", country_name)
                    fg.add_entry("Group Type", "joined")
                    fg.add_entry("Group Members", str_countries_in_group)
                    shortcut_coef_output(fg, group_coef)

            # output diversified groups
            for joined_div_group in group_manager.joined_div_groups[product_name]:
                str_countries_in_group = ""
                for country_name in joined_div_group.get_countries_in_group():
                    str_countries_in_group += country_name + ";"
                for country_name in joined_div_group.get_countries_in_group():
                    fg.add_entry("Country", country_name)
                    fg.add_entry("Group Type", "div. joined")
                    fg.add_entry("Group Members", str_countries_in_group)
                    country_coef = joined_div_group.get_coef_for_country(country_name)
                    shortcut_coef_output(fg, country_coef)

    if input_manager.ctrl.general_settings.toggle_graphical_output:
        # visual output
        if input_manager.ctrl.industry_settings.use_gdp_as_x:
            x_label = "GDP"
        else:
            x_label = "Time"
        if input_manager.ctrl.industry_settings.production_quantity_calc_per_capita:
            y_label = product_name + " Amount per Capita"
        else:
            y_label = product_name + " Amount"

        day_dir = get_day_folder_path(input_manager)
        directory = ensure_directory_exists(day_dir / Path(folder) / "visual_output" / "Country Groups")

        for product_name in input_manager.industry_input.dict_product_input.keys():

            # output joined groups
            group_id = 0
            joined_groups: [CountryGroupJoined] = group_manager.joined_groups[product_name]
            for joined_group in joined_groups:
                historical_data = joined_group.get_all_historical_data()

                historical_tds = [tds for (_, tds) in historical_data]

                colors = itertools.cycle(sns.color_palette())
                for country_name, tds in historical_data:
                    country_color = next(colors)

                    # plot historical data for each country
                    plot_historical_data(tds, country_color, country_name)

                # plot coefficients of group
                group_coef = joined_group.get_coef()
                interval = get_series_range(historical_tds)
                plot_coef_in_range("Group", interval, group_coef, next(colors), next(colors), next(colors))

                filename = product_name + "_Joined-Group-" + str(group_id)
                image_label = product_name + " - Joined Group " + str(group_id)

                save_plot(image_label, x_label, y_label, directory, filename)
            group_id += 1

            # output diversified groups
            group_id = 0
            div_groups: [CountryGroupJoinedDiversified] = group_manager.joined_div_groups[product_name]
            for div_group in div_groups:
                historical_data = div_group.get_all_historical_data()

                colors = itertools.cycle(sns.color_palette())
                for country_name, tds in historical_data:
                    country_color = next(colors)

                    # plot historical data
                    interval = get_series_range([tds])
                    plot_historical_data(tds, country_color, country_name)

                    # plot coefficients of country
                    country_coef = div_group.get_coef_for_country(country_name)
                    plot_coef_in_range(country_name, interval, country_coef,
                                       country_color, country_color, country_color)

                filename = product_name + "_Div-Group-" + str(group_id)
                image_label = product_name + " - Div Group " + str(group_id)

                save_plot(image_label, x_label, y_label, directory, filename)
            group_id += 1


def generate_visual_output(folder, input_manager: input.Input, countries_pp: dict[str, CountryPreprocessed]):

    # generate vis output specific consumption
    for product_name in input_manager.industry_input.dict_product_input.keys():
        x_label = "Time"
        y_label = "Specific Consumption"
        directory = Path(folder) / "visual_output" / "Specific Consumption"
        for country_name, country_pp in countries_pp.items():
            sc_pp = country_pp.industry_pp.products_pp[product_name].specific_consumption_pp
            if sc_pp.historical_sc_available:
                series_el = sc_pp.specific_consumption_historical[DemandType.ELECTRICITY]
                series_el.get_coef().set_method(ForecastMethod.LINEAR)
                series_he = sc_pp.specific_consumption_historical[DemandType.HEAT]
                series_he.get_coef().set_method(ForecastMethod.LINEAR)
                series_hy = sc_pp.specific_consumption_historical[DemandType.HYDROGEN]
                series_hy.get_coef().set_method(ForecastMethod.LINEAR)
                save_multiple_series_plot(input_manager, directory,
                                          [series_el, series_he, series_hy],
                                          ["electricity", "heat", "hydrogen"],
                                          x_label, y_label, country_name, product_name)

    # generate vis output amount_vs_year
    for product_name, product_input in input_manager.industry_input.dict_product_input.items():
        x_label = "Time"
        y_label = product_name + " Amount"
        directory = Path(folder) / "visual_output" / (y_label + "-vs-" + x_label)
        for country_name, country_pp in countries_pp.items():
            series = country_pp.industry_pp.products_pp[product_name].amount_vs_year
            if not (series.is_empty() or series.is_zero()):
                save_series_plot(input_manager, directory, series, x_label, y_label, country_name, product_name)

    # generate vis output amount_per_capita_vs_year
    for product_name, product_input in input_manager.industry_input.dict_product_input.items():
        x_label = "Time"
        y_label = product_name + " Amount-per-Capita"
        directory = Path(folder) / "visual_output" / (y_label + "-vs-" + x_label)
        for country_name, country_pp in countries_pp.items():
            series: TwoDseries = country_pp.industry_pp.products_pp[product_name].amount_per_capita_vs_year
            if not (series.is_empty() or series.is_zero()):
                save_series_plot(input_manager, directory, series, x_label, y_label, country_name, product_name)

    # generate vis output amount_per_capita_vs_gdp
    for product_name, product_input in input_manager.industry_input.dict_product_input.items():
        x_label = "GDP"
        y_label = product_name + " Amount-per-Capita"
        directory = Path(folder) / "visual_output" / (y_label + "-vs-" + x_label)
        for country_name, country_pp in countries_pp.items():
            series = country_pp.industry_pp.products_pp[product_name].amount_per_capita_vs_gdp
            if not (series.is_empty() or series.is_zero()):
                save_series_plot(input_manager, directory, series, x_label, y_label, country_name, product_name)

    # generate vis output amount_vs_gdp
    for product_name, product_input in input_manager.industry_input.dict_product_input.items():
        x_label = "GDP"
        y_label = product_name + " Amount"
        directory = Path(folder) / "visual_output" / (y_label + "-vs-" + x_label)
        for country_name, country_pp in countries_pp.items():
            series = country_pp.industry_pp.products_pp[product_name].amount_vs_gdp
            if not (series.is_empty() or series.is_zero()):
                save_series_plot(input_manager, directory, series, x_label, y_label, country_name, product_name)


def _get_all_product_pps(product_name: str, countries_pp: dict[str, CountryPreprocessed]) -> [ProductPreprocessed]:
    """ Shortcut to get all preprocessed products of all countries of a product type. """
    return [country_pp.industry_pp.products_pp[product_name]
            for country_pp in countries_pp.values()
            if product_name in country_pp.industry_pp.products_pp.keys()]


def generate_amount_timeseries_output(folder, input_manager: input.Input, countries_pp: dict[str, CountryPreprocessed]):
    """ Generate the output for preprocessed timeseries related to amount of products. """

    filename = "ind_coef_product_amount_vs_time.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.dict_product_input.items():
            fg.start_sheet(product_name)

            all_tss = \
                [product_pp.amount_vs_year for product_pp in _get_all_product_pps(product_name, countries_pp)]
            year_range = get_series_range(all_tss)

            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    ts = products_pp[product_name].amount_vs_year
                    generate_timeseries_output(fg, ts, year_range)
                else:
                    generate_timeseries_output(fg, Timeseries([]), year_range)

    filename = "ind_coef_product_amount_per_capita_vs_time.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.dict_product_input.items():
            fg.start_sheet(product_name)

            all_tss = \
                [product_pp.amount_per_capita_vs_year for product_pp in _get_all_product_pps(product_name, countries_pp)]
            year_range = get_series_range(all_tss)

            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    ts = products_pp[product_name].amount_per_capita_vs_year
                    generate_timeseries_output(fg, ts, year_range)
                else:
                    generate_timeseries_output(fg, Timeseries([]), year_range)


def generate_amount_per_gdp_coef_output(folder, input_manager: input.Input,
                                        countries_pp: dict[str, CountryPreprocessed]):
    """ Generate the output of preprocessed coefficients for the product amount, with the x-axis being gdp. """

    filename = "ind_coef_product_amount_vs_gdp.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.dict_product_input.items():
            fg.start_sheet(product_name)
            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    ts = products_pp[product_name].amount_vs_gdp
                    shortcut_coef_output(fg, ts.get_coef())
                else:
                    shortcut_coef_output(fg, Coef())

    filename = "ind_coef_product_amount_per_capita_vs_gdp.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.dict_product_input.items():
            fg.start_sheet(product_name)
            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    ts = products_pp[product_name].amount_per_capita_vs_gdp
                    shortcut_coef_output(fg, ts.get_coef())
                else:
                    shortcut_coef_output(fg, Coef())


def generate_specific_consumption_output(folder, input_manager: input.Input,
                                         countries_pp: dict[str, CountryPreprocessed]):
    """ Generate all output related to preprocessed specific consumption. """
    products_has_his_sc = input_manager.industry_input.sc_historical_data_file_names.keys()

    filename = "ind_coef_specific_consumption_.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name in products_has_his_sc:
            fg.start_sheet(product_name + "_heat")
            all_tss = \
                [product_pp.specific_consumption_pp.specific_consumption_historical[DemandType.HEAT]
                 for product_pp in _get_all_product_pps(product_name, countries_pp)
                 if DemandType.HEAT in product_pp.specific_consumption_pp.specific_consumption_historical.keys()]
            year_range = get_series_range(all_tss)
            if year_range[0] is None or year_range[1] is None:
                continue

            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp

                if product_name in products_pp.keys():
                    sc_pp = products_pp[product_name].specific_consumption_pp
                    ts: Timeseries
                    if DemandType.HEAT in sc_pp.specific_consumption_historical.keys():
                        ts = sc_pp.specific_consumption_historical[DemandType.HEAT]
                    else:
                        ts = Timeseries([])
                    generate_timeseries_output(fg, ts, year_range)
                else:
                    generate_timeseries_output(fg, Timeseries([(0, 0)]), year_range)

            fg.start_sheet(product_name + "_electricity")
            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp
                all_tss = \
                    [product_pp.specific_consumption_pp.specific_consumption_historical[DemandType.ELECTRICITY]
                     for product_pp in _get_all_product_pps(product_name, countries_pp)
                     if DemandType.ELECTRICITY
                     in product_pp.specific_consumption_pp.specific_consumption_historical.keys()]
                year_range = get_series_range(all_tss)

                if product_name in products_pp.keys():
                    sc_pp = products_pp[product_name].specific_consumption_pp
                    ts: Timeseries
                    if DemandType.ELECTRICITY in sc_pp.specific_consumption_historical.keys():
                        ts = sc_pp.specific_consumption_historical[DemandType.ELECTRICITY]
                    else:
                        ts = Timeseries([])
                    generate_timeseries_output(fg, ts, year_range)
                else:
                    generate_timeseries_output(fg, Timeseries([(0, 0)]), year_range)
