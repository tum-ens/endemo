"""
This module contains all functions that generate output files from a model instance.
"""
from __future__ import annotations

import math
import shutil
from pathlib import Path

import numpy as np

from endemo2.data_structures.conversions_unit import convert, Unit, get_conversion_scalar
from endemo2.input_and_settings.input_households import HouseholdsSubsectorId
from endemo2.input_and_settings.input_manager import InputManager
from endemo2.input_and_settings.input_transport import TransportInput
from endemo2.model_instance.instance_filter.cts_instance_filter import CtsInstanceFilter
from endemo2.model_instance.instance_filter.general_instance_filter import CountryInstanceFilter
from endemo2.model_instance.instance_filter.households_instance_filter import HouseholdsInstanceFilter
from endemo2.model_instance.instance_filter.industry_instance_filter import ProductInstanceFilter, \
    IndustryInstanceFilter
from endemo2.model_instance.instance_filter.transport_instance_filter import TransportInstanceFilter
from endemo2.model_instance.model.country import Country
from endemo2.data_structures.containers import Demand, SpecConsum
from endemo2.model_instance.model.cts.cts_sector import CommercialTradeServices
from endemo2.model_instance.model.households.household_sector import Households
from endemo2.model_instance.model.industry.products import Product
from endemo2.model_instance.model.transport.transport_sector import Transport
from endemo2.output.output_utility import FileGenerator, shortcut_demand_table, get_day_folder_path, \
    ensure_directory_exists
from endemo2.model_instance.model.industry.industry_sector import Industry
from endemo2.data_structures.enumerations import SectorIdentifier, ForecastMethod, DemandType, TrafficType, \
    TransportModal
from endemo2.data_structures.conversions_string import map_hh_subsector_to_string, map_tra_modal_to_string, \
    map_tra_traffic_type_to_string, map_demand_to_string

# toggles to further control which output is written, maybe adapt them into settings later
IND_HOURLY_DEMAND_DISABLE = False
CTS_HOURLY_DEMAND_DISABLE = False
HH_HOURLY_DEMAND_DISABLE = False

TOGGLE_GEN_OUTPUT = True
TOGGLE_DETAILED_OUTPUT = True


def generate_instance_output(input_manager: InputManager, countries: dict[str, Country],
                             country_instance_filter: CountryInstanceFilter,
                             product_instance_filter: ProductInstanceFilter,
                             industry_instance_filter: IndustryInstanceFilter,
                             cts_instance_filter: CtsInstanceFilter,
                             hh_instance_filter: HouseholdsInstanceFilter,
                             tra_instance_filter: TransportInstanceFilter):
    """
    Calls all generate_x_output functions of this module that should be used to generate output.
    """

    # decide output folder name for scenario
    str_forecast_method = ""
    match input_manager.ctrl.industry_settings.forecast_method:
        case ForecastMethod.LINEAR:
            str_forecast_method = "lin"
        case ForecastMethod.QUADRATIC:
            str_forecast_method = "quadr"

    x_axis = ""
    match input_manager.ctrl.industry_settings.use_gdp_as_x:
        case True:
            x_axis = "gdp"
        case False:
            x_axis = "time"

    geo_res = ""
    match input_manager.ctrl.general_settings.toggle_nuts2_resolution:
        case True:
            geo_res = "nuts2"
        case False:
            geo_res = "country"

    str_target_year = str(input_manager.ctrl.general_settings.target_year)
    scenario_output_folder_name = \
        "scenario_" + str_target_year + "_ind_" + str_forecast_method + "_" + x_axis + "_" + geo_res

    # create directory when not present
    day_folder = get_day_folder_path(input_manager)
    scenario_folder = ensure_directory_exists(day_folder / scenario_output_folder_name)
    if TOGGLE_DETAILED_OUTPUT:
        details_folder = ensure_directory_exists(scenario_folder / "details")

    # copy Set_and_Control_Parameters that lead to this instance output to output folder
    shutil.copy(InputManager.ctrl_path, scenario_folder / "Set_and_Control_Parameters.xlsx")

    # shortcut toggles
    toggle_nuts2 = input_manager.ctrl.general_settings.toggle_nuts2_resolution
    toggle_hourly = input_manager.ctrl.general_settings.toggle_hourly_forecast
    active_sectors = input_manager.ctrl.general_settings.get_active_sectors()

    # generate all outputs according to settings
    if TOGGLE_GEN_OUTPUT:
        output_gen_gdp(scenario_folder, input_manager, countries, country_instance_filter)
        output_gen_population_forecast(scenario_folder, input_manager, countries, country_instance_filter)
        if TOGGLE_DETAILED_OUTPUT:
            output_gen_population_forecast_details(details_folder, input_manager, countries, country_instance_filter)
    if SectorIdentifier.INDUSTRY in active_sectors:
        if not toggle_nuts2:
            output_ind_demand_country(scenario_folder, input_manager, countries)
        if toggle_nuts2:
            output_ind_demand_nuts2(scenario_folder, input_manager, countries)
        if toggle_hourly and not toggle_nuts2 and not IND_HOURLY_DEMAND_DISABLE:
            output_ind_demand_hourly_country(scenario_folder, input_manager, countries)
        if toggle_hourly and toggle_nuts2 and not IND_HOURLY_DEMAND_DISABLE:
            output_ind_demand_hourly_nuts2(scenario_folder, input_manager, countries)
        if TOGGLE_DETAILED_OUTPUT:
            output_ind_product_amount(details_folder, input_manager, countries, product_instance_filter)
            output_ind_specific_consumption(details_folder, input_manager, countries, product_instance_filter)
    if SectorIdentifier.COMMERCIAL_TRADE_SERVICES in active_sectors:
        if not toggle_nuts2:
            output_cts_demand_country(scenario_folder, input_manager, countries)
        if toggle_nuts2:
            output_cts_demand_nuts2(scenario_folder, input_manager, countries)
        if toggle_hourly and not toggle_nuts2 and not CTS_HOURLY_DEMAND_DISABLE:
            output_cts_demand_hourly_country(scenario_folder, input_manager, countries)
        if toggle_hourly and toggle_nuts2 and not CTS_HOURLY_DEMAND_DISABLE:
            output_cts_demand_hourly_nuts2(scenario_folder, input_manager, countries)
        if TOGGLE_DETAILED_OUTPUT:
            output_cts_employee_number(details_folder, input_manager, countries, cts_instance_filter)
            output_cts_specific_consumption(details_folder, input_manager, countries, cts_instance_filter)
    if SectorIdentifier.HOUSEHOLDS in active_sectors:
        if not toggle_nuts2:
            output_hh_demand_country(scenario_folder, input_manager, countries)
        if toggle_nuts2:
            output_hh_demand_nuts2(scenario_folder, input_manager, countries)
        if toggle_hourly and not toggle_nuts2 and not HH_HOURLY_DEMAND_DISABLE:
            output_hh_demand_hourly_country(scenario_folder, input_manager, countries)
        if toggle_hourly and toggle_nuts2 and not HH_HOURLY_DEMAND_DISABLE:
            pass
        if TOGGLE_DETAILED_OUTPUT:
            output_hh_characteristics(details_folder, input_manager, countries, hh_instance_filter)
            output_hh_subsectors_demand(details_folder, input_manager, countries, hh_instance_filter)
    if SectorIdentifier.TRANSPORT in active_sectors:
        output_tra_energy_demand_country(scenario_folder, input_manager, countries)
        output_tra_kilometers(scenario_folder, input_manager, tra_instance_filter)
        if toggle_nuts2:
            output_tra_energy_demand_nuts2(scenario_folder, input_manager, countries)
            output_tra_kilometers_nuts2(scenario_folder, input_manager, tra_instance_filter)
        if TOGGLE_DETAILED_OUTPUT:
            output_tra_modal_split(details_folder, input_manager, tra_instance_filter)
            output_tra_production_volume(details_folder, input_manager, industry_instance_filter,
                                         product_instance_filter)
            output_tra_energy_demand_detail(details_folder, input_manager, countries)


def output_gen_gdp(folder: Path, input_manager: InputManager, countries,
                   country_instance_filter: CountryInstanceFilter):
    """ Generates all output related to the gdp of a countries. """
    target_year = input_manager.ctrl.general_settings.target_year

    filename = "gen_gdp_forecast.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("Prognosis")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            fg.add_entry(target_year, country_instance_filter.get_gdp_in_target_year(country_name))


def output_gen_population_forecast(folder: Path, input_manager: InputManager, countries,
                                   country_instance_filter: CountryInstanceFilter):
    """ Generates all output related to the population of a countries. """
    target_year = input_manager.ctrl.general_settings.target_year

    filename = "gen_population_forecast.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("Country Forecast")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            fg.add_entry(target_year, country_instance_filter.get_population_country_in_target_year(country_name))

        fg.start_sheet("NUTS2 Forecast")
        for country_name in countries.keys():
            regions_perc = country_instance_filter.get_population_nuts2_percentages_in_target_year(country_name)
            country_pop = country_instance_filter.get_population_country_in_target_year(country_name)
            for region_name, value in regions_perc.items():
                fg.add_entry("NUTS2 Region", region_name)
                fg.add_entry(target_year, country_pop * value)


def output_gen_population_forecast_details(folder: Path, input_manager: InputManager, countries,
                                           country_instance_filter: CountryInstanceFilter):
    """ Generates all output related to the population of a countries. """
    target_year = input_manager.ctrl.general_settings.target_year

    filename = "gen_population_forecast_details.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("Country Forecast")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            fg.add_entry(target_year, country_instance_filter.get_population_country_in_target_year(country_name))

        fg.start_sheet("Country Forecast Distributed by NUTS2 Density")
        for country_name in countries.keys():
            regions_perc = country_instance_filter.get_population_nuts2_percentages_in_target_year(country_name)
            country_pop = country_instance_filter.get_population_country_in_target_year(country_name)
            for region_name, value in regions_perc.items():
                fg.add_entry("NUTS2 Region", region_name)
                fg.add_entry(target_year, country_pop * value)

        fg.start_sheet("NUTS2 Separate Forecast")
        for country_name in countries.keys():
            regions_pop = country_instance_filter.get_population_nuts2_in_target_year(country_name)
            for region_name, value in regions_pop.items():
                fg.add_entry("NUTS2 Region", region_name)
                fg.add_entry(target_year, value)

        fg.start_sheet("NUTS2 Sum")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            nuts2_sum = country_instance_filter.get_population_nuts2_sum(country_name)
            fg.add_entry(target_year, nuts2_sum)

        fg.start_sheet("NUTS2 Population Density")
        for country_name in countries.keys():
            regions_perc = country_instance_filter.get_population_nuts2_percentages_in_target_year(country_name)
            for region_name, value in regions_perc.items():
                fg.add_entry("NUTS2 Region", region_name)
                fg.add_entry(target_year, value)


def output_ind_product_amount(folder: Path, input_manager: InputManager, countries,
                              product_instance_filter: ProductInstanceFilter):
    """ Generates all output related to amount of a subsector. """

    filename = "ind_product_amount_forecast_" + str(input_manager.ctrl.general_settings.target_year) + ".xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        dict_sum = dict[str, float]()
        for product_name, product_obj in input_manager.industry_input.dict_product_input.items():
            fg.start_sheet(product_name)
            for country_name, country in countries.items():
                if country_name not in dict_sum.keys():
                    dict_sum[country_name] = 0.0
                fg.add_entry("Country", country_name)
                try:
                    perc_used = product_instance_filter.get_perc_used(product_name)
                    product_amount = product_instance_filter.get_amount(country_name, product_name) * perc_used / 1000
                    dict_sum[country_name] += product_amount
                    fg.add_entry("Amount [kt]", product_amount)
                except KeyError:
                    # country doesn't have product
                    fg.add_entry("Amount [kt]", "")
        fg.start_sheet("IND")
        for country_name, amount_sum in dict_sum.items():
            fg.add_entry("Country", country_name)
            fg.add_entry("Amount [kt]", amount_sum)


def output_ind_demand_country(folder: Path, input_manager: InputManager, countries):
    """ Generates industry demand output of a countries. """

    filename = "ind_demand_forecast_per_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.dict_product_input.items():
            fg.start_sheet(product_name)
            for country_name, country in countries.items():
                fg.add_entry("Country", country_name)
                industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
                product: Product = industry.get_product(product_name)
                demand: Demand = product.calculate_demand()
                shortcut_demand_table(fg, demand)

        fg.start_sheet("forecasted")
        for country_name, country in countries.items():
            fg.add_entry("Country", country_name)
            demand: Demand = \
                country.get_sector(SectorIdentifier.INDUSTRY).calculate_forecasted_demand()
            shortcut_demand_table(fg, demand)

        fg.start_sheet("rest")
        for country_name, country in countries.items():
            fg.add_entry("Country", country_name)
            industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
            demand: Demand = industry.calculate_rest_sector_demand()
            shortcut_demand_table(fg, demand)

        fg.start_sheet("IND")
        for country_name, country in countries.items():
            fg.add_entry("Country", country_name)
            industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
            demand: Demand = industry.calculate_total_demand()
            shortcut_demand_table(fg, demand)


def output_ind_demand_nuts2(folder: Path, input_manager: InputManager, countries):
    """ Generates industry demand output for nuts2 regions. """

    filename = "ind_demand_forecast_per_nuts2.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.dict_product_input.items():
            fg.start_sheet(product_name)
            for country in countries.values():
                industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
                product: Product = industry.get_product(product_name)
                dict_nuts2_demand: dict[str, Demand] = product.get_demand_distributed_by_nuts2()
                for nuts2_region_name, demand in dict_nuts2_demand.items():
                    fg.add_entry("NUTS2 Region", nuts2_region_name)
                    shortcut_demand_table(fg, demand)

            fg.start_sheet("forecasted")
            for country in countries.values():
                industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
                dict_nuts2_demand = industry.calculate_forecasted_demand_distributed_by_nuts2()
                for nuts2_region_name, demand in dict_nuts2_demand.items():
                    fg.add_entry("NUTS2 Region", nuts2_region_name)
                    shortcut_demand_table(fg, demand)

            fg.start_sheet("rest")
            for country in countries.values():
                industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
                dict_nuts2_demand = industry.calculate_rest_demand_distributed_by_nuts2()
                for nuts2_region_name, demand in dict_nuts2_demand.items():
                    fg.add_entry("NUTS2 Region", nuts2_region_name)
                    shortcut_demand_table(fg, demand)

            fg.start_sheet("IND")
            for country in countries.values():
                industry: Industry = country.get_sector(SectorIdentifier.INDUSTRY)
                dict_nuts2_demand = industry.calculate_total_demand_distributed_by_nuts2()
                for nuts2_region_name, demand in dict_nuts2_demand.items():
                    fg.add_entry("NUTS2 Region", nuts2_region_name)
                    shortcut_demand_table(fg, demand)


def output_cts_employee_number(folder: Path, input_manager: InputManager, countries,
                               cts_instance_filter: CtsInstanceFilter):
    """ Generates output for the number of employees in the cts sector. """

    filename = "cts_employee_number_forecast.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("Employees Country")
        for country_name, country in countries.items():
            fg.add_entry("Country", country_name)
            cts_sector: CommercialTradeServices = country.get_sector(SectorIdentifier.COMMERCIAL_TRADE_SERVICES)
            population = cts_instance_filter.get_population_country(country_name)
            employee_sum = 0
            for subsector in cts_sector.get_subsectors():
                employee_pop_share = \
                    cts_instance_filter.get_employee_share_of_population_country(country_name, subsector)
                num_employees_in_sector = employee_pop_share * population
                employee_sum += num_employees_in_sector
                fg.add_entry(subsector, num_employees_in_sector)
            fg.add_entry("Employees total", employee_sum)

        fg.start_sheet("Employees NUTS2")
        for country_name, country in countries.items():
            cts_sector: CommercialTradeServices = country.get_sector(SectorIdentifier.COMMERCIAL_TRADE_SERVICES)
            nuts2_population = cts_instance_filter.get_population_nuts2(country_name)
            for region_name, population in nuts2_population.items():
                fg.add_entry("NUTS2", region_name)
                employee_sum = 0
                for subsector in cts_sector.get_subsectors():
                    employee_pop_share = \
                        cts_instance_filter.get_employee_share_of_population_nuts2(country_name, subsector)[
                            region_name]
                    num_employees_in_sector = employee_pop_share * population
                    employee_sum += num_employees_in_sector
                    fg.add_entry(subsector, num_employees_in_sector)
                fg.add_entry("Employees total", employee_sum)


def output_cts_demand_country(folder: Path, input_manager: InputManager, countries):
    """ Generates all demand output for the cts sector. """

    filename = "cts_demand_forecast_by_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("CTS")
        for country_name, country in countries.items():
            fg.add_entry("Country", country_name)
            cts: CommercialTradeServices = country.get_sector(SectorIdentifier.COMMERCIAL_TRADE_SERVICES)
            demand = cts.calculate_demand()
            shortcut_demand_table(fg, demand)


def output_cts_demand_nuts2(folder: Path, input_manager: InputManager, countries):
    """ Generates all demand output for the cts sector. """

    filename = "cts_demand_forecast_by_nuts2.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("CTS")
        for country_name, country in countries.items():
            cts: CommercialTradeServices = country.get_sector(SectorIdentifier.COMMERCIAL_TRADE_SERVICES)
            dict_nuts2_demand = cts.calculate_demand_distributed_by_nuts2()
            for nuts2_region_name, demand in dict_nuts2_demand.items():
                fg.add_entry("NUTS2 Region", nuts2_region_name)
                shortcut_demand_table(fg, demand)


def output_ind_demand_hourly_country(folder: Path, input_manager: InputManager, countries):
    """ Generates the output that splits the demand into the hourly timeseries for each country. """

    filename = "ind_demand_forecast_hourly_per_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("IND")
        fg.add_complete_column("t", list(range(1, 8760 + 1)))
        for country_name, country in countries.items():
            hourly_demand = country.get_sector(SectorIdentifier.INDUSTRY).calculate_total_hourly_demand()
            fg.add_complete_column(country_name + ".Elec", hourly_demand[DemandType.ELECTRICITY])
            fg.add_complete_column(country_name + ".Q1", [h.q1 for h in hourly_demand[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".Q2", [h.q2 for h in hourly_demand[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".Q3", [h.q3 for h in hourly_demand[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".Q4", [h.q4 for h in hourly_demand[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".Hydro", hourly_demand[DemandType.HYDROGEN])


def output_ind_demand_hourly_nuts2(folder: Path, input_manager: InputManager, countries):
    """ Generates the output that splits the demand into the hourly timeseries for nuts2 regions. """

    filename = "ind_demand_forecast_hourly_per_nuts2.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("IND")
        fg.add_complete_column("t", list(range(1, 8760 + 1)))
        for country_name, country in countries.items():
            hourly_demand_nuts2 = \
                country.get_sector(
                    SectorIdentifier.INDUSTRY).calculate_total_hourly_demand_distributes_by_nuts2()
            for region_name, hourly_demand in hourly_demand_nuts2.items():
                fg.add_complete_column(region_name + ".Elec", hourly_demand[DemandType.ELECTRICITY])
                fg.add_complete_column(region_name + ".Q1", [h.q1 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".Q2", [h.q2 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".Q3", [h.q3 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".Q4", [h.q4 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".Hydro", hourly_demand[DemandType.HYDROGEN])


def output_cts_demand_hourly_country(folder: Path, input_manager: InputManager, countries):
    """ Generates the output that splits the demand into the hourly timeseries for each country. """

    filename = "cts_demand_forecast_hourly_per_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("CTS")
        fg.add_complete_column("t", list(range(1, 8760 + 1)))
        for country_name, country in countries.items():
            hourly_demand = country.get_sector(
                SectorIdentifier.COMMERCIAL_TRADE_SERVICES).calculate_hourly_demand()
            fg.add_complete_column(country_name + ".Elec", hourly_demand[DemandType.ELECTRICITY])
            fg.add_complete_column(country_name + ".Q1", [h.q1 for h in hourly_demand[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".Q2", [h.q2 for h in hourly_demand[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".Hydro", hourly_demand[DemandType.HYDROGEN])


def output_cts_demand_hourly_nuts2(folder: Path, input_manager: InputManager, countries):
    """ Generates the output that splits the demand into the hourly timeseries for nuts2 regions. """

    filename = "cts_demand_forecast_hourly_per_nuts2.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("CTS")
        fg.add_complete_column("t", list(range(1, 8760 + 1)))
        for country_name, country in countries.items():
            hourly_demand_nuts2 = country.get_sector(SectorIdentifier.COMMERCIAL_TRADE_SERVICES) \
                .calculate_hourly_demand_distributed_by_nuts2()
            for region_name, hourly_demand in hourly_demand_nuts2.items():
                fg.add_complete_column(region_name + ".Elec", hourly_demand[DemandType.ELECTRICITY])
                fg.add_complete_column(region_name + ".Q1", [h.q1 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".Q2", [h.q2 for h in hourly_demand[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".Hydro", hourly_demand[DemandType.HYDROGEN])


def output_ind_specific_consumption(folder: Path, input_manager: InputManager, countries,
                                    product_if: ProductInstanceFilter):
    """ Generates all output related to the specific consumption of products. """

    filename = "ind_specific_consumption_forecast.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        for product_name, product_obj in input_manager.industry_input.dict_product_input.items():
            fg.start_sheet(product_name)
            for country_name in countries.keys():
                fg.add_entry("Country", country_name)
                try:
                    sc: SpecConsum = product_if.get_specific_consumption(country_name, product_name)
                    fg.add_entry("Electricity [TWh/t]", sc.electricity)
                    fg.add_entry("Heat [TWh/t]", sc.heat)
                    fg.add_entry("Hydrogen [TWh/t]", sc.hydrogen)
                    fg.add_entry("max. subst. of heat with H2 [%]", sc.max_subst_h2)
                except KeyError:
                    # country doesn't product product
                    fg.add_entry("Electricity [TWh/t]", "")
                    fg.add_entry("Heat [TWh/t]", "")
                    fg.add_entry("Hydrogen [TWh/t]", "")
                    fg.add_entry("max. subst. of heat with H2 [%]", "")


def output_cts_specific_consumption(folder: Path, input_manager: InputManager, countries,
                                    cts_if: CtsInstanceFilter):
    """ Generates all output related to the specific consumption of employees. """

    filename = "cts_specific_consumption_forecast.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("CTS")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            try:
                sc: SpecConsum = cts_if.get_specific_consumption(country_name)
                fg.add_entry("Electricity [TWh/t]", sc.electricity)
                fg.add_entry("Heat [TWh/t]", sc.heat)
                fg.add_entry("Hydrogen [TWh/t]", sc.hydrogen)
                fg.add_entry("max. subst. of heat with H2 [%]", sc.max_subst_h2)
            except KeyError:
                # country doesn't product product
                fg.add_entry("Electricity [TWh/t]", "")
                fg.add_entry("Heat [TWh/t]", "")
                fg.add_entry("Hydrogen [TWh/t]", "")
                fg.add_entry("max. subst. of heat with H2 [%]", "")


def output_hh_characteristics(folder: Path, input_manager: InputManager, countries, hh_if: HouseholdsInstanceFilter):
    """ Generates the households characteristics output. """
    filename = "hh_characteristics.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("Test")  # todo remove?
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            pers_per_household = hh_if.get_avg_persons_per_household_in_target_year(country_name)
            fg.add_entry("Person per Household [Pers./Household]", pers_per_household)
            area_per_household = hh_if.get_area_per_household_in_target_year(country_name)
            fg.add_entry("Area per Household [m^2/Household]", area_per_household)
            spec_energy = hh_if.get_space_heating_specific_heat_in_target_year(country_name)
            fg.add_entry("Specific energy consumption [kWh/m^2]", convert(Unit.TWh, Unit.kWh, spec_energy))
            population = hh_if.get_population_in_target_year(country_name)
            avg_num_person_per_household = hh_if.get_avg_persons_per_household_in_target_year(country_name)
            num_households = population / avg_num_person_per_household
            area_total = hh_if.get_area_per_household_in_target_year(country_name) * num_households
            fg.add_entry("Living area total [m^2]", area_total)
            fg.add_entry("Population", population)

        fg.start_sheet("Pers per Household")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            pers_per_household = hh_if.get_avg_persons_per_household_in_target_year(country_name)
            fg.add_entry("Person per Household [Pers./Household]", pers_per_household)

        fg.start_sheet("Area per Household")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            area_per_household = hh_if.get_area_per_household_in_target_year(country_name)
            fg.add_entry("Area per Household [m^2/Household]", area_per_household)

        fg.start_sheet("Specific energy consumption")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            spec_energy = hh_if.get_space_heating_specific_heat_in_target_year(country_name)
            fg.add_entry("Specific energy consumption [kWh/m^2]", convert(Unit.TWh, Unit.kWh, spec_energy))

        fg.start_sheet("Living area total")
        for country_name in countries.keys():
            fg.add_entry("Country", country_name)
            population = hh_if.get_population_in_target_year(country_name)
            avg_num_person_per_household = hh_if.get_avg_persons_per_household_in_target_year(country_name)
            num_households = population / avg_num_person_per_household
            area_total = hh_if.get_area_per_household_in_target_year(country_name) * num_households
            fg.add_entry("Living area total [m^2]", area_total)


def output_hh_subsectors_demand(folder: Path, input_manager: InputManager, countries, hh_if: HouseholdsInstanceFilter):
    """ Generates the simplified demand output of the subsectors. """

    filename = "hh_subsectors_energy_demand.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("Energy_PerSubsector")
        for country_name, country_obj in countries.items():
            fg.add_entry("Country", country_name)

            households_sector: Households = country_obj.get_sector(SectorIdentifier.HOUSEHOLDS)

            total_demand = 0
            for subsector_id in hh_if.get_subsectors():
                subsector_name = map_hh_subsector_to_string[subsector_id].replace("_", " ")

                subsector_demand = households_sector._subsectors[subsector_id].calculate_demand()
                energy_demand = subsector_demand.get_sum()

                fg.add_entry(subsector_name + " [TWh]", energy_demand)
                total_demand += energy_demand

            fg.add_entry("total [TWh]", total_demand)

        fg.start_sheet("Energy_Useful_Total")
        for country_name, country_obj in countries.items():
            fg.add_entry("Country", country_name)

            households_sector: Households = country_obj.get_sector(SectorIdentifier.HOUSEHOLDS)
            households_demand = households_sector.calculate_demand()

            fg.add_entry("Electricity [TWh]", households_demand.electricity)
            fg.add_entry("Heat [TWh]", households_demand.heat.get_sum())
            fg.add_entry("Hydrogen [TWh]", households_demand.hydrogen)
            fg.add_entry("Total [TWh]", households_demand.get_sum())


def output_hh_demand_country(folder: Path, input_manager: InputManager, countries):
    """ Generates the demand output of the households sector distributed by country. """

    filename = "hh_demand_forecast_per_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("HH")
        for country_name, country_obj in countries.items():
            fg.add_entry("Country", country_name)

            households_sector: Households = country_obj.get_sector(SectorIdentifier.HOUSEHOLDS)
            hh_demand = households_sector.calculate_demand()
            shortcut_demand_table(fg, hh_demand)


def output_hh_demand_nuts2(folder: Path, input_manager: InputManager, countries):
    """ Generates the demand output of the households sector distributed by nuts2 regions. """

    filename = "hh_demand_forecast_per_nuts2.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("HH")
        for country_name, country_obj in countries.items():
            households_sector: Households = country_obj.get_sector(SectorIdentifier.HOUSEHOLDS)
            hh_demand_nuts2 = households_sector.calculate_demand_distributed_by_nuts2()
            for region_name, demand in hh_demand_nuts2.items():
                fg.add_entry("NUTS2 Region", region_name)
                shortcut_demand_table(fg, demand)


def output_hh_demand_hourly_country(folder: Path, input_manager: InputManager, countries):
    """ Generates the demand output of the households sector distributed by country. """

    filename = "hh_demand_forecast_hourly_per_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("CTS")
        fg.add_complete_column("t", list(range(1, 8760 + 1)))
        for country_name, country in countries.items():
            hourly_demand_efh = country.get_sector(
                SectorIdentifier.HOUSEHOLDS).calculate_hourly_demand_efh()
            hourly_demand_mfh = country.get_sector(
                SectorIdentifier.HOUSEHOLDS).calculate_hourly_demand_mfh()

            electricity = [he + hm for (he, hm)
                           in zip(hourly_demand_efh[DemandType.ELECTRICITY], hourly_demand_mfh[DemandType.ELECTRICITY])]

            fg.add_complete_column(country_name + ".Elec", electricity)
            fg.add_complete_column(country_name + ".EFH_Q1", [h.q1 for h in hourly_demand_efh[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".EFH_Q2", [h.q2 for h in hourly_demand_efh[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".EFH_H2", hourly_demand_efh[DemandType.HYDROGEN])
            fg.add_complete_column(country_name + ".MFH_Q1", [h.q1 for h in hourly_demand_mfh[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".MFH_Q2", [h.q2 for h in hourly_demand_mfh[DemandType.HEAT]])
            fg.add_complete_column(country_name + ".MFH_H2", hourly_demand_mfh[DemandType.HYDROGEN])


def output_hh_demand_hourly_nuts2(folder: Path, input_manager: InputManager, countries):
    """ Generates the demand output of the households sector distributed by nuts2 regions. """

    filename = "hh_demand_forecast_hourly_per_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("CTS")
        fg.add_complete_column("t", list(range(1, 8760 + 1)))
        for country_name, country in countries.items():
            hourly_demand_efh_nuts2 = country.get_sector(
                SectorIdentifier.HOUSEHOLDS).calculate_hourly_demand_efh_distributed_by_nuts2()
            hourly_demand_mfh_nuts2 = country.get_sector(
                SectorIdentifier.HOUSEHOLDS).calculate_hourly_demand_mfh_distributed_by_nuts2()

            for region_name in hourly_demand_efh_nuts2.keys():
                hourly_demand_efh = hourly_demand_efh_nuts2[region_name]
                hourly_demand_mfh = hourly_demand_mfh_nuts2[region_name]

                electricity = [he + hm for (he, hm)
                               in zip(hourly_demand_efh[DemandType.ELECTRICITY],
                                      hourly_demand_mfh[DemandType.ELECTRICITY])]

                fg.add_complete_column(region_name + ".Elec", electricity)
                fg.add_complete_column(region_name + ".EFH_Q1", [h.q1 for h in hourly_demand_efh[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".EFH_Q2", [h.q2 for h in hourly_demand_efh[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".EFH_H2", hourly_demand_efh[DemandType.HYDROGEN])
                fg.add_complete_column(region_name + ".MFH_Q1", [h.q1 for h in hourly_demand_mfh[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".MFH_Q2", [h.q2 for h in hourly_demand_mfh[DemandType.HEAT]])
                fg.add_complete_column(region_name + ".MFH_H2", hourly_demand_mfh[DemandType.HYDROGEN])


def output_tra_modal_split(folder: Path, input_manager: InputManager, traffic_if: TransportInstanceFilter):
    """ The modal split output for the transport sector. """

    filename = "tra_modal_split_" + str(input_manager.ctrl.general_settings.target_year) + ".xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("Pt Modal Split")
        for country_name in input_manager.ctrl.general_settings.active_countries:
            fg.add_entry("Country", country_name)
            for modal_group_id in TransportInput.tra_modal_split_groups[TrafficType.PERSON]:
                for modal_id in TransportInput.tra_modal_split_groups[TrafficType.PERSON][modal_group_id]:
                    share = traffic_if.get_modal_share_in_target_year(country_name, TrafficType.PERSON, modal_id)
                    modal_string = map_tra_modal_to_string[modal_id]
                    fg.add_entry("pt " + modal_string + " [%]", share * 100)

        fg.start_sheet("Ft Modal Split")
        for country_name in input_manager.ctrl.general_settings.active_countries:
            fg.add_entry("Country", country_name)
            for modal_group_id in TransportInput.tra_modal_split_groups[TrafficType.FREIGHT]:
                for modal_id in TransportInput.tra_modal_split_groups[TrafficType.FREIGHT][modal_group_id]:
                    share = traffic_if.get_modal_share_in_target_year(country_name, TrafficType.FREIGHT, modal_id)
                    modal_string = map_tra_modal_to_string[modal_id]
                    fg.add_entry("ft " + modal_string + " [%]", share * 100)


def output_tra_production_volume(folder: Path, input_manager: InputManager,
                                 industry_if: IndustryInstanceFilter, product_if: ProductInstanceFilter):
    """ Outputs the historical quantities of the industry sector that are used for transport sector calculations. """

    target_year = input_manager.ctrl.general_settings.target_year
    reference_year = input_manager.ctrl.transport_settings.ind_production_reference_year

    filename = "tra_production_volume.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("total " + str(target_year))
        for country_name in input_manager.ctrl.general_settings.active_countries:
            fg.add_entry("Country", country_name)
            amount = product_if.get_product_amount_sum_country_in_target_year(country_name)
            fg.add_entry("Amount [t]", amount)

        fg.start_sheet("total " + str(reference_year))
        for country_name in input_manager.ctrl.general_settings.active_countries:
            fg.add_entry("Country", country_name)
            amount = product_if.get_product_amount_historical_in_year(country_name, reference_year)
            fg.add_entry("Amount [t]", amount)

        fg.start_sheet("single " + str(reference_year))
        for country_name in input_manager.ctrl.general_settings.active_countries:
            fg.add_entry("Country", country_name)
            for subsector_name in input_manager.ctrl.industry_settings.active_product_names:
                perc_used = product_if.get_perc_used(subsector_name)
                amount = product_if.get_historical_amount(country_name, subsector_name, reference_year) * perc_used
                fg.add_entry(subsector_name + " [t]", amount)


def output_tra_kilometers(folder: Path, input_manager: InputManager, traffic_if: TransportInstanceFilter):
    """ Outputs the forecast kilometers for each traffic type. """

    filename = "tra_traffic_kilometers_" + str(input_manager.ctrl.general_settings.target_year) + ".xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("Person kilometers")
        for country_name in input_manager.ctrl.general_settings.active_countries:
            fg.add_entry("Country", country_name)
            sum = 0.0
            for modal_id in TransportInput.tra_modal_lists[TrafficType.PERSON]:
                ukm = traffic_if.get_unit_km_country_in_target_year(country_name, TrafficType.PERSON, modal_id)
                ukm = convert(Unit.Standard, Unit.Billion, ukm)
                modal_string = map_tra_modal_to_string[modal_id]
                sum += ukm
                fg.add_entry("pt " + modal_string + " [Mrd. pkm]", ukm)
            fg.add_entry("pt total [Mrd. pkm]", sum)

        fg.start_sheet("Tonne kilometers")
        for country_name in input_manager.ctrl.general_settings.active_countries:
            fg.add_entry("Country", country_name)
            sum = 0.0
            for modal_id in TransportInput.tra_modal_lists[TrafficType.FREIGHT]:
                ukm = traffic_if.get_unit_km_country_in_target_year(country_name, TrafficType.FREIGHT, modal_id)
                ukm = convert(Unit.Standard, Unit.Million, ukm)
                modal_string = map_tra_modal_to_string[modal_id]
                sum += ukm
                fg.add_entry("ft " + modal_string + " [Mil. tkm]", ukm)
            fg.add_entry("ft total [Mil. tkm]", sum)


def output_tra_kilometers_nuts2(folder: Path, input_manager: InputManager, traffic_if: TransportInstanceFilter):
    """ Outputs the forecast kilometers for each traffic type. """

    filename = "tra_traffic_kilometers_nuts2_" + str(input_manager.ctrl.general_settings.target_year) + ".xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("Person kilometers")
        for country_name in input_manager.ctrl.general_settings.active_countries:
            for region_name in traffic_if.get_nuts2_region_names(country_name):
                fg.add_entry("NUTS2 Region", region_name)
                sum = 0.0
                for modal_id in TransportInput.tra_modal_lists[TrafficType.PERSON]:
                    ukm = traffic_if.get_unit_km_nuts2_in_target_year(country_name, region_name, TrafficType.PERSON,
                                                                      modal_id)
                    ukm = convert(Unit.Standard, Unit.Billion, ukm)

                    modal_string = map_tra_modal_to_string[modal_id]
                    sum += ukm
                    fg.add_entry("pt " + modal_string + " [Mrd. pkm]", ukm)
                fg.add_entry("pt total [Mrd. pkm]", sum)

        fg.start_sheet("Tonne kilometers")
        for country_name in input_manager.ctrl.general_settings.active_countries:
            for region_name in traffic_if.get_nuts2_region_names(country_name):
                fg.add_entry("NUTS2 Region", region_name)
                sum = 0.0
                for modal_id in TransportInput.tra_modal_lists[TrafficType.FREIGHT]:
                    ukm = \
                        traffic_if.get_unit_km_nuts2_in_target_year(country_name, region_name, TrafficType.FREIGHT,
                                                                    modal_id)

                    ukm = convert(Unit.Standard, Unit.Million, ukm)

                    modal_string = map_tra_modal_to_string[modal_id]
                    sum += ukm
                    fg.add_entry("ft " + modal_string + " [Mil. tkm]", ukm)
                fg.add_entry("ft total [Mil. tkm]", sum)


def output_tra_energy_demand_detail(folder: Path, input_manager: InputManager, countries):
    """ Output the forecasted energy demand split by modals. """

    for traffic_type in [TrafficType.PERSON, TrafficType.FREIGHT]:
        filename = "tra_energy_demand_" + map_tra_traffic_type_to_string[traffic_type] + "_" \
                   + str(input_manager.ctrl.general_settings.target_year) + ".xlsx"

        dict_total_energy_carrier = dict[str, dict[DemandType, float]]()

        fg = FileGenerator(input_manager, folder, filename)
        with fg:
            for demand_type in [DemandType.ELECTRICITY, DemandType.HYDROGEN, DemandType.FUEL]:
                fg.start_sheet(map_demand_to_string[demand_type] + " per country")
                for country_name, country_obj in countries.items():
                    fg.add_entry("Country", country_name)

                    if country_name not in dict_total_energy_carrier.keys():
                        dict_total_energy_carrier[country_name] = dict[DemandType]()

                    for modal_id in TransportInput.tra_modal_lists[traffic_type]:
                        modal_string = map_tra_modal_to_string[modal_id]
                        transport_sector: Transport = country_obj.get_sector(SectorIdentifier.TRANSPORT)
                        demand: Demand = transport_sector.calculate_subsector_demand(traffic_type)[modal_id]
                        consumption = demand.get(demand_type)
                        consumption = convert(Unit.kWh, Unit.TWh, consumption)

                        fg.add_entry(modal_string + " [TWh]", consumption)

                        if demand_type not in dict_total_energy_carrier[country_name]:
                            dict_total_energy_carrier[country_name][demand_type] = 0.0
                        dict_total_energy_carrier[country_name][demand_type] += consumption

                    fg.add_entry("total [TWh]", dict_total_energy_carrier[country_name][demand_type])

            fg.start_sheet("total per country")
            for country_name, country_obj in countries.items():
                fg.add_entry("Country", country_name)
                for demand_type in [DemandType.ELECTRICITY, DemandType.HYDROGEN, DemandType.FUEL]:
                    fg.add_entry("total " + map_demand_to_string[demand_type] + " [TWh]",
                                 dict_total_energy_carrier[country_name][demand_type])


def output_tra_energy_demand_country(folder: Path, input_manager: InputManager, countries):
    """ Output the forecasted energy demand. """

    filename = "tra_demand_forecast_per_country.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("TRA")
        for country_name, country_obj in countries.items():
            fg.add_entry("Country", country_name)

            transport_sector: Transport = country_obj.get_sector(SectorIdentifier.TRANSPORT)
            tra_demand = transport_sector.calculate_demand()
            tra_demand.scale(get_conversion_scalar(Unit.kWh, Unit.TWh))
            fg.add_entry("Electricity [TWh]", tra_demand.electricity)
            fg.add_entry("Heat [TWh]", tra_demand.heat.get_sum())
            fg.add_entry("Hydrogen [TWh]", tra_demand.hydrogen)
            fg.add_entry("Fuel [TWh]", tra_demand.fuel)


def output_tra_energy_demand_nuts2(folder: Path, input_manager: InputManager, countries):
    """ Generates the demand output of the transport sector distributed by nuts2 regions. """

    filename = "tra_demand_forecast_per_nuts2.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("TRA")
        for country_name, country_obj in countries.items():
            transport_sector: Transport = country_obj.get_sector(SectorIdentifier.TRANSPORT)
            tra_demand_nuts2 = transport_sector.calculate_demand_distributed_by_nuts2()
            for region_name, demand in tra_demand_nuts2.items():
                fg.add_entry("NUTS2 Region", region_name)
                demand.scale(get_conversion_scalar(Unit.kWh, Unit.TWh))
                shortcut_demand_table(fg, demand)


def output_tra_demand_hourly(folder: Path, input_manager: InputManager, countries):
    """ Generates the hourly demand output for the transport sector. """

    filename = "tra_demand_forecast_hourly.xlsx"
    fg = FileGenerator(input_manager, folder, filename)
    with fg:
        fg.start_sheet("TRA")

        fg.add_complete_column("t", np.arange(1, 8760 + 1))

        load_profile: dict = input_manager.transport_input.load_profile

        for country_name, country_obj in countries.items():
            transport_sector: Transport = country_obj.get_sector(SectorIdentifier.TRANSPORT)
            person_demand = transport_sector.calculate_demand_for_traffic_type(TrafficType.PERSON)
            freight_demand = transport_sector.calculate_demand_for_traffic_type(TrafficType.FREIGHT)

            fg.add_complete_column(
                country_name + ".Elec" + "road",    #todo: better
                person_demand.electricity
                * load_profile[(TrafficType.PERSON, TransportModal.road, DemandType.HYDROGEN)])
            fg.add_complete_column(
                country_name + ".Elec",
                person_demand.electricity
                * load_profile[(TrafficType.PERSON, TransportModal.road, DemandType.HYDROGEN)])




