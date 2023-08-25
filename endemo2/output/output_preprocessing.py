"""
This module contains all functions that generate output files from the preprocessor.
"""
from __future__ import  annotations

from endemo2.data_structures.conversions_string import map_demand_to_string, map_hh_subsector_to_string, \
    map_tra_modal_to_string, map_tra_traffic_type_to_string
from endemo2.data_structures.enumerations import DemandType, ScForecastMethod, SectorIdentifier, TransportModal, \
    TrafficType
from endemo2.input_and_settings.input_cts import CtsInput
from endemo2.input_and_settings.input_households import hh_subsectors
from endemo2.input_and_settings.input_transport import TransportInput
from endemo2.output.output_utility import generate_timeseries_output, \
    shortcut_coef_output, get_day_folder_path, ensure_directory_exists
from endemo2.data_structures.prediction_models import Timeseries
from endemo2.preprocessing.preproccessing_step_two import GroupManager, CountryGroupJoinedDiversified, \
    CountryGroupJoined
from endemo2.preprocessing.preprocessing_step_one import CountryPreprocessed, ProductPreprocessed
from endemo2.output.output_utility_visual import *
from endemo2.preprocessing.preprocessor import Preprocessor
from endemo2.utility import get_series_range

# additional output settings, maybe get them from an Excel file later
TOGGLE_IND_PRODUCT_AMOUNT_VISUAL_OUTPUT = False
TOGGLE_IND_COUNTRY_GROUP_VISUAL_OUTPUT = False
TOGGLE_IND_SPECIFIC_CONSUMPTION_VISUAL_OUTPUT = False

TOGGLE_CTS_SPECIFIC_CONSUMPTION_VISUAL_OUTPUT = False
TOGGLE_CTS_EMPLOYEE_COUNTRY_VISUAL_OUTPUT = False
TOGGLE_CTS_EMPLOYEE_NUTS2_VISUAL_OUTPUT = False

TOGGLE_HH_CONSUMPTION_VISUAL_OUTPUT = False

TOGGLE_TRA_MODAL_SPLIT_VISUAL_OUTPUT = True


def generate_preprocessing_output(input_manager: InputManager, preprocessor: Preprocessor):
    """
    Calls all generate_x_output functions of this module that should be used to generate output of the preprocessor.
    """
    day_folder = get_day_folder_path(input_manager)
    preprocessing_folder = day_folder / "preprocessed"

    # shortcut variables
    countries_pp = preprocessor.countries_pp
    active_sectors = input_manager.ctrl.general_settings.get_active_sectors()

    # files output for active sectors
    if SectorIdentifier.INDUSTRY in active_sectors:
        output_ind_country_group(preprocessing_folder, input_manager, preprocessor.group_manager)
        output_ind_coef_product_amount(preprocessing_folder, input_manager, countries_pp)
        output_ind_specific_consumption(preprocessing_folder, input_manager, countries_pp)
    if SectorIdentifier.COMMERCIAL_TRADE_SERVICES in active_sectors:
        output_cts_specific_consumption(preprocessing_folder, input_manager, countries_pp)
        output_cts_coef_employee_number(preprocessing_folder, input_manager, countries_pp)
    if SectorIdentifier.HOUSEHOLDS in active_sectors:
        output_hh_coef_historical_consumption(preprocessing_folder, input_manager, countries_pp)
        output_hh_demand_historical_2018(preprocessing_folder, input_manager, countries_pp)
    if SectorIdentifier.TRANSPORT in active_sectors:
        output_tra_coef_modal_split(preprocessing_folder, input_manager, countries_pp)

    # visual output
    if SectorIdentifier.INDUSTRY in active_sectors:
        if TOGGLE_IND_COUNTRY_GROUP_VISUAL_OUTPUT:
            output_ind_country_group_visual(preprocessing_folder, input_manager, preprocessor.group_manager)
        if TOGGLE_IND_PRODUCT_AMOUNT_VISUAL_OUTPUT:
            output_ind_product_amount_visual(preprocessing_folder, input_manager, countries_pp)
        if TOGGLE_IND_SPECIFIC_CONSUMPTION_VISUAL_OUTPUT:
            output_ind_specific_consumption_visual(preprocessing_folder, input_manager, countries_pp)

    if SectorIdentifier.COMMERCIAL_TRADE_SERVICES in active_sectors:
        if TOGGLE_CTS_SPECIFIC_CONSUMPTION_VISUAL_OUTPUT:
            output_cts_specific_consumption_visual(preprocessing_folder, input_manager, countries_pp)
        if TOGGLE_CTS_EMPLOYEE_COUNTRY_VISUAL_OUTPUT:
            output_cts_employee_number_visual_country(preprocessing_folder, input_manager, countries_pp)
        if TOGGLE_CTS_EMPLOYEE_NUTS2_VISUAL_OUTPUT:
            output_cts_employee_number_visual_nuts2(preprocessing_folder, input_manager, countries_pp)

    if SectorIdentifier.HOUSEHOLDS in active_sectors:
        if TOGGLE_HH_CONSUMPTION_VISUAL_OUTPUT:
            output_hh_consumption_visual_country(preprocessing_folder, input_manager, countries_pp)

    if SectorIdentifier.TRANSPORT in active_sectors:
        if TOGGLE_TRA_MODAL_SPLIT_VISUAL_OUTPUT:
            output_tra_modal_split_visual(preprocessing_folder, input_manager, countries_pp)


def output_ind_country_group(folder, input_manager: InputManager, group_manager: GroupManager):
    """ Generate industry group coefficient output. """

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
                    shortcut_coef_output(fg, group_coef)

            # output diversified groups
            for joined_div_group in group_manager.joined_div_groups[product_name]:
                str_countries_in_group = ""
                for country_name in joined_div_group.get_countries_in_group():
                    str_countries_in_group += country_name + ";"
                for country_name in joined_div_group.get_countries_in_group():
                    fg.add_entry("Country", country_name)
                    fg.add_entry("Group Type", "div. joined")
                    country_coef = joined_div_group.get_coef_for_country(country_name)
                    shortcut_coef_output(fg, country_coef)


def output_ind_country_group_visual(folder: Path, input_manager: InputManager, group_manager: GroupManager):
    """ Creates the visual output of country groups in the industry sector. """

    country_groups_folder = ensure_directory_exists(folder / "visual_output" / "Country Groups")

    for product_name in input_manager.industry_input.dict_product_input.keys():

        # set axis labels
        if input_manager.ctrl.industry_settings.use_gdp_as_x:
            x_label = "GDP"
        else:
            x_label = "Time"
        if input_manager.ctrl.industry_settings.production_quantity_calc_per_capita:
            y_label = product_name + " Amount per Capita"
        else:
            y_label = product_name + " Amount"

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
            plot_coef_in_range("Group", interval, group_coef, next(colors), next(colors), next(colors), next(colors))

            filename = product_name + "_Joined-Group-" + str(group_id)
            image_label = product_name + " - Joined Group " + str(group_id)

            save_plot(image_label, x_label, y_label, country_groups_folder, filename)
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
                                   country_color, country_color, country_color, country_color)

            filename = product_name + "_Div-Group-" + str(group_id)
            image_label = product_name + " - Div Group " + str(group_id)

            save_plot(image_label, x_label, y_label, country_groups_folder, filename)
        group_id += 1


def output_ind_product_amount_visual(folder, input_manager: InputManager, countries_pp: dict[str, CountryPreprocessed]):
    """ Generate visual output for product amount in the industry sector. """
    # generate vis output amount_vs_year
    for product_name, product_input in input_manager.industry_input.dict_product_input.items():
        x_label = "Time"
        y_label = product_name + " Amount"
        directory = Path(folder) / "visual_output" / ("IND_" + (y_label + "-vs-" + x_label))
        for country_name, country_pp in countries_pp.items():
            series = country_pp.industry_pp.products_pp[product_name].amount_vs_year
            if not (series.is_empty() or series.is_zero()):
                save_series_plot(input_manager, directory, series, x_label, y_label, country_name, product_name)

    # generate vis output amount_per_capita_vs_year
    for product_name, product_input in input_manager.industry_input.dict_product_input.items():
        x_label = "Time"
        y_label = product_name + " Amount-per-Capita"
        directory = Path(folder) / "visual_output" / ("IND_" + (y_label + "-vs-" + x_label))
        for country_name, country_pp in countries_pp.items():
            series: TwoDseries = country_pp.industry_pp.products_pp[product_name].amount_per_capita_vs_year
            if not (series.is_empty() or series.is_zero()):
                save_series_plot(input_manager, directory, series, x_label, y_label, country_name, product_name)

    # generate vis output amount_per_capita_vs_gdp
    for product_name, product_input in input_manager.industry_input.dict_product_input.items():
        x_label = "GDP"
        y_label = product_name + " Amount-per-Capita"
        directory = Path(folder) / "visual_output" / ("IND_" + (y_label + "-vs-" + x_label))
        for country_name, country_pp in countries_pp.items():
            series = country_pp.industry_pp.products_pp[product_name].amount_per_capita_vs_gdp
            if not (series.is_empty() or series.is_zero()):
                save_series_plot(input_manager, directory, series, x_label, y_label, country_name, product_name)

    # generate vis output amount_vs_gdp
    for product_name, product_input in input_manager.industry_input.dict_product_input.items():
        x_label = "GDP"
        y_label = product_name + " Amount"
        directory = Path(folder) / "visual_output" / ("IND_" + (y_label + "-vs-" + x_label))
        for country_name, country_pp in countries_pp.items():
            series = country_pp.industry_pp.products_pp[product_name].amount_vs_gdp
            if not (series.is_empty() or series.is_zero()):
                save_series_plot(input_manager, directory, series, x_label, y_label, country_name, product_name)


def output_ind_specific_consumption_visual(folder: Path, input_manager: InputManager,
                                           countries_pp: dict[str, CountryPreprocessed]):
    """ Generate visual output for specific consumption in the industry sector. """
    for product_name in input_manager.industry_input.dict_product_input.keys():
        x_label = "Time"
        y_label = "Specific Consumption"
        directory = folder / "visual_output" / "IND Specific Consumption"
        for country_name, country_pp in countries_pp.items():
            sc_pp = country_pp.industry_pp.products_pp[product_name].specific_consumption_pp
            if sc_pp.historical_sc_available:
                dict_series_output = dict[str, TwoDseries]()
                for demand_type in [DemandType.ELECTRICITY, DemandType.HEAT, DemandType.HYDROGEN]:
                    series = sc_pp.specific_consumption_historical[demand_type]
                    series.get_coef().set_method(ForecastMethod.LINEAR)
                    dict_series_output[map_demand_to_string[demand_type]] = series
                save_multiple_series_plot(input_manager, directory,
                                          dict_series_output.values(),
                                          dict_series_output.keys(),
                                          x_label, y_label, country_name, product_name)


def output_cts_specific_consumption_visual(folder: Path, input_manager: InputManager,
                                           countries_pp: dict[str, CountryPreprocessed]):
    """ Generate visual output for specific consumption in the cts sector. """
    for subsector in CtsInput.subsector_names:
        x_label = "Time"
        y_label = "Specific Consumption"
        directory = folder / "visual_output" / "CTS Specific Consumption"
        for country_name, country_pp in countries_pp.items():
            dict_series_output = dict[str, Timeseries]()
            for demand_type in [DemandType.ELECTRICITY, DemandType.HEAT, DemandType.HYDROGEN]:
                sc_ts = country_pp.cts_pp.specific_consumption[demand_type]
                sc_coef = sc_ts.get_coef()
                sc_forecast_method = input_manager.ctrl.cts_settings.trend_calc_for_spec
                match sc_forecast_method:
                    case ScForecastMethod.LINEAR:
                        sc_coef.set_method(ForecastMethod.LINEAR)
                    case ScForecastMethod.CONST_MEAN:
                        mean_y = sc_ts.get_mean_y()
                        (last_year, _) = sc_ts.get_last_data_entry()
                        sc_coef.set_exp((last_year, mean_y), 0.0)
                        sc_coef.set_method(ForecastMethod.EXPONENTIAL)
                    case ScForecastMethod.CONST_LAST:
                        (last_year, last_value) = sc_ts.get_last_data_entry()
                        sc_coef.set_exp((last_year, last_value), 0.0)
                        sc_coef.set_method(ForecastMethod.EXPONENTIAL)
                dict_series_output[map_demand_to_string[demand_type]] = sc_ts

            save_multiple_series_plot(input_manager, directory,
                                      dict_series_output.values(),
                                      dict_series_output.keys(),
                                      x_label, y_label, country_name, subsector)


def output_cts_employee_number_visual_country(folder: Path, input_manager: InputManager,
                                              countries_pp: dict[str, CountryPreprocessed]):
    """ Generate visual output for the number of employees in the cts sector per country. """
    for subsector in CtsInput.subsector_names:
        x_label = "Time"
        y_label = "Number of Employees"
        directory = folder / "visual_output" / "CTS Number of Employees in Country"
        for country_name, country_pp in countries_pp.items():
            series = country_pp.cts_pp.employee_share_in_subsector_country[subsector]
            if not (series.is_empty() or series.is_zero()):
                save_series_plot(input_manager, directory, series, x_label, y_label, country_name, subsector)


def output_cts_employee_number_visual_nuts2(folder: Path, input_manager: InputManager,
                                            countries_pp: dict[str, CountryPreprocessed]):
    """ Generate visual output for the number of employees in the cts sector per nuts2 region. """
    for subsector in CtsInput.subsector_names:
        x_label = "Time"
        y_label = "Number of Employees"
        directory = folder / "visual_output" / "CTS Number of Employees in NUTS2"
        for country_name, country_pp in countries_pp.items():
            for region_name in [leaf.region_name for leaf
                                in country_pp.nuts2_pp.population_prognosis_tree_root.get_all_leaf_nodes()]:
                series = country_pp.cts_pp.employee_share_in_subsector_nuts2[region_name][subsector]
                if not (series.is_empty() or series.is_zero()):
                    save_series_plot(input_manager, directory, series, x_label, y_label, region_name, subsector)


def _get_all_product_pps(product_name: str, countries_pp: dict[str, CountryPreprocessed]) -> [ProductPreprocessed]:
    """ Shortcut to get all preprocessed products of all countries of a product type. """
    return [country_pp.industry_pp.products_pp[product_name]
            for country_pp in countries_pp.values()
            if product_name in country_pp.industry_pp.products_pp.keys()]


def output_ind_coef_product_amount(folder, input_manager: InputManager, countries_pp: dict[str, CountryPreprocessed]):
    """ Generate the output for preprocessed coefficients related to amount of products. """

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
                [product_pp.amount_per_capita_vs_year for product_pp in
                 _get_all_product_pps(product_name, countries_pp)]
            year_range = get_series_range(all_tss)

            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                products_pp = country_pp.industry_pp.products_pp
                if product_name in products_pp.keys():
                    ts = products_pp[product_name].amount_per_capita_vs_year
                    generate_timeseries_output(fg, ts, year_range)
                else:
                    generate_timeseries_output(fg, Timeseries([]), year_range)

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


def output_ind_specific_consumption(folder, input_manager: InputManager,
                                    countries_pp: dict[str, CountryPreprocessed]):
    """ Generate all output related to preprocessed specific consumption of the industry sector. """
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


def output_cts_specific_consumption(folder, input_manager: InputManager,
                                    countries_pp: dict[str, CountryPreprocessed]):
    """ Generate all output related to preprocessed specific consumption of the cts sector. """

    filename = "cts_coef_specific_consumption_.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("electricity_timeseries")
        electricity_tss = [country_pp.cts_pp.specific_consumption[DemandType.ELECTRICITY]
                           for country_pp in countries_pp.values()]
        year_range = get_series_range(electricity_tss)
        for ts in electricity_tss:
            generate_timeseries_output(fg, ts, year_range)

        fg.start_sheet("heat_timeseries")
        heat_tss = [country_pp.cts_pp.specific_consumption[DemandType.HEAT]
                    for country_pp in countries_pp.values()]
        year_range = get_series_range(heat_tss)
        for ts in heat_tss:
            generate_timeseries_output(fg, ts, year_range)

        fg.start_sheet("hydrogen_timeseries")
        hydrogen_tss = [country_pp.cts_pp.specific_consumption[DemandType.HYDROGEN]
                        for country_pp in countries_pp.values()]
        year_range = get_series_range(hydrogen_tss)
        for ts in hydrogen_tss:
            generate_timeseries_output(fg, ts, year_range)

        fg.start_sheet("electricity_mean")
        for ts in electricity_tss:
            fg.add_entry("Mean specific demand [GWh/tsd. employees]", ts.get_mean_y())

        fg.start_sheet("heat_mean")
        for ts in heat_tss:
            fg.add_entry("Mean specific demand [GWh/tsd. employees]", ts.get_mean_y())

        fg.start_sheet("hydrogen_mean")
        for ts in hydrogen_tss:
            fg.add_entry("Mean specific demand [GWh/tsd. employees]", ts.get_mean_y())


def output_cts_coef_employee_number(folder, input_manager: InputManager, countries_pp: dict[str, CountryPreprocessed]):
    """ Generates coefficient output for the number of employees in the cts sector. """

    filename = "cts_coef_employee_number_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for subsector in CtsInput.subsector_names:
            fg.start_sheet(subsector)

            all_tss = [country_pp.cts_pp.employee_share_in_subsector_country[subsector]
                       for country_pp in countries_pp.values()]
            year_range = get_series_range(all_tss)

            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                employee_share_country = country_pp.cts_pp.employee_share_in_subsector_country[subsector]
                generate_timeseries_output(fg, employee_share_country, year_range)

    filename = "cts_coef_employee_number_nuts2.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for subsector in CtsInput.subsector_names:
            fg.start_sheet(subsector)

            all_tss = [dict_nuts2_employee_share[subsector]
                       for dict_nuts2_employee_share in country_pp.cts_pp.employee_share_in_subsector_nuts2.values()]
            year_range = get_series_range(all_tss)

            for country_name, country_pp in countries_pp.items():
                for region_name, dict_employee_share in country_pp.cts_pp.employee_share_in_subsector_nuts2.items():
                    fg.add_entry("NUTS2", region_name)
                    employee_share_nuts2 = dict_employee_share[subsector]
                    generate_timeseries_output(fg, employee_share_nuts2, year_range)


def output_hh_coef_historical_consumption(folder, input_manager: InputManager,
                                          countries_pp: dict[str, CountryPreprocessed]):
    """ Generates coefficient output for the historical consumption of the households sector. """

    filename = "hh_coef_historical_consumption.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for subsector_id in hh_subsectors:
            str_subsector = map_hh_subsector_to_string[subsector_id]
            for demand_type in [DemandType.ELECTRICITY, DemandType.HEAT, DemandType.HYDROGEN]:
                str_demand_type = map_demand_to_string[demand_type]
                fg.start_sheet(str_subsector + "_" + str_demand_type)

                all_tss = [country_pp.households_pp.sectors_pp[subsector_id][demand_type]
                           for _, country_pp in countries_pp.items()]
                year_range = get_series_range(all_tss)

                for country_name, country_pp in countries_pp.items():
                    fg.add_entry("Country", country_name)
                    hh_pp = country_pp.households_pp
                    ts_historical = hh_pp.sectors_pp[subsector_id][demand_type]
                    generate_timeseries_output(fg, ts_historical, year_range)


def output_hh_demand_historical_2018(folder, input_manager: InputManager,
                                     countries_pp: dict[str, CountryPreprocessed]):
    """ Generates historical demand output for the households sector in 2018. """
    target_year = 2018

    filename = "hh_subsectors_energy_demand_2018.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for subsector_id in hh_subsectors:
            str_subsector = map_hh_subsector_to_string[subsector_id]
            fg.start_sheet(str_subsector)

            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                subsector_pp = country_pp.households_pp.sectors_pp[subsector_id]
                demand_sum = 0
                for demand_type in [DemandType.ELECTRICITY, DemandType.HEAT, DemandType.HYDROGEN]:
                    demand_sum += subsector_pp[demand_type].get_value_at_year_else_zero(target_year)
                fg.add_entry("Consumption 2018 [TWh]", demand_sum)


def output_hh_consumption_visual_country(folder, input_manager: InputManager,
                                         countries_pp: dict[str, CountryPreprocessed]):
    """ Generates the visual output for each country and subsectors energy consumption in the households sector. """

    for country_name, country_pp in countries_pp.items():
        for subsector_id, dict_subsector_consumption in country_pp.households_pp.sectors_pp.items():
            subsector_name = map_hh_subsector_to_string[subsector_id]

            x_label = "Time"
            y_label = subsector_name + " Consumption"
            directory = folder / "visual_output" / "HH Consumption"

            dict_series_output = dict[str, TwoDseries]()
            for demand_type in [DemandType.ELECTRICITY, DemandType.HEAT, DemandType.HYDROGEN]:
                series = dict_subsector_consumption[demand_type]
                series.get_coef().set_method(ForecastMethod.LINEAR)
                dict_series_output[map_demand_to_string[demand_type]] = series
            save_multiple_series_plot(input_manager, directory,
                                      dict_series_output.values(),
                                      dict_series_output.keys(),
                                      x_label, y_label, country_name, subsector_name)


def output_tra_coef_modal_split(folder, input_manager: InputManager,
                                countries_pp: dict[str, CountryPreprocessed]):
    """ Generates coefficient output for the historical modal split. """

    filename = "tra_person_coef_modal_split.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for modal_id in itertools.chain.from_iterable(
                TransportInput.tra_modal_split_groups[TrafficType.PERSON].values()):
            fg.start_sheet(str(modal_id))

            all_tss = [country_pp.transport_pp.modal_split_timeseries[TrafficType.PERSON][modal_id]
                       for country_pp in countries_pp.values()]
            year_range = get_series_range(all_tss)

            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                ts_modal_split = country_pp.transport_pp.modal_split_timeseries[TrafficType.PERSON][modal_id]
                generate_timeseries_output(fg, ts_modal_split, year_range)

    filename = "tra_freight_coef_modal_split.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for modal_id in itertools.chain.from_iterable(
                TransportInput.tra_modal_split_groups[TrafficType.FREIGHT].values()):
            fg.start_sheet(str(modal_id))

            all_tss = [country_pp.transport_pp.modal_split_timeseries[TrafficType.FREIGHT][modal_id]
                       for country_pp in countries_pp.values()]
            year_range = get_series_range(all_tss)

            for country_name, country_pp in countries_pp.items():
                fg.add_entry("Country", country_name)
                ts_modal_split = country_pp.transport_pp.modal_split_timeseries[TrafficType.FREIGHT][modal_id]
                generate_timeseries_output(fg, ts_modal_split, year_range)


def output_tra_modal_split_visual(folder, input_manager: InputManager,
                                  countries_pp: dict[str, CountryPreprocessed]):
    """ Generates the visual output for each country and modal split in the transport sector. """

    for traffic_type in TransportInput.tra_modal_lists.keys():
        for country_name, country_pp in countries_pp.items():
            for modal_group_id in TransportInput.tra_modal_split_groups[traffic_type].keys():
                str_modal_group = map_tra_modal_to_string[modal_group_id]
                x_label = "Time"
                y_label = "Percentage of " + str_modal_group
                directory = \
                    folder / "visual_output" / "TRA Modal Split" / map_tra_traffic_type_to_string[traffic_type]

                dict_series_output = dict[str, TwoDseries]()
                for modal_id in TransportInput.tra_modal_split_groups[traffic_type][modal_group_id]:
                    series = country_pp.transport_pp.modal_split_timeseries[traffic_type][modal_id]
                    series.get_coef().set_method(ForecastMethod.LINEAR)
                    dict_series_output[map_tra_modal_to_string[modal_id]] = series
                save_multiple_series_plot(input_manager, directory,
                                          dict_series_output.values(),
                                          dict_series_output.keys(),
                                          x_label, y_label, country_name, str_modal_group)

